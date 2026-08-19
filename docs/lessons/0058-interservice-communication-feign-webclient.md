---
icon: lucide/arrow-left-right
---

# 0058: Inter-service communication: RestTemplate, WebClient, and Spring Cloud OpenFeign

In a microservices architecture, services rarely operate in isolation. An Order Service must query the Customer Service for address verification, reserve stock with the Inventory Service, and invoke the Payment Gateway.

Spring provides four distinct HTTP client paradigms:
1. **`RestTemplate`**: The legacy synchronous blocking HTTP client (now in maintenance mode).
2. **`WebClient`**: The reactive, non-blocking HTTP client from Spring WebFlux.
3. **`RestClient`**: The modern fluent synchronous HTTP client introduced in Spring Framework 6.1 / Spring Boot 3.2+.
4. **`Spring Cloud OpenFeign`**: A declarative HTTP client that generates runtime client proxies from annotated Java interfaces.

In this lesson, you will master configuring declarative OpenFeign clients, propagating security headers with Feign `RequestInterceptor`, decoding error responses with `ErrorDecoder`, and comparing client trade-offs.

---

## 1. Inter-service communication architecture

``` mermaid
flowchart TD
    subgraph CallerService["Order Service (Spring Boot)"]
        OrderController["OrderController"]
        OrderService["OrderService"]
        
        subgraph ClientTier["HTTP Client Choices"]
            FeignProxy["PaymentFeignClient (Declarative Interface Proxy)"]
            RestClientBean["RestClient (Fluent Synchronous)"]
            WebClientBean["WebClient (Non-Blocking Reactive)"]
        end
        
        SecurityInterceptor["Feign RequestInterceptor (JWT & TraceContext Propagation)"]
        ErrorDecoderImpl["Custom Feign ErrorDecoder (4xx/5xx Mapping)"]
        
        OrderController --> OrderService
        OrderService --> FeignProxy
        OrderService --> RestClientBean
        OrderService --> WebClientBean
        
        FeignProxy --> SecurityInterceptor
        SecurityInterceptor --> ErrorDecoderImpl
    end

    subgraph CalleeService["Payment Service (Remote Microservice)"]
        PaymentAPI["PaymentController (/api/v1/payments)"]
    end

    SecurityInterceptor -->|HTTP POST with Bearer Token & TraceParent| PaymentAPI
```

---

## 2. Spring http client comparison matrix

| Client | Programming Model | Introduced / Status | Best Used For |
| :--- | :--- | :--- | :--- |
| **`RestTemplate`** | Imperative / Blocking | Spring 3.0 (Maintenance Mode). | Legacy codebases; new code should use `RestClient`. |
| **`RestClient`** | Fluent / Synchronous | Spring 6.1 (Spring Boot 3.2+). | Modern imperative REST calls with builder syntax. |
| **`WebClient`** | Reactive / Non-Blocking | Spring 5.0 (Spring WebFlux). | High-scale reactive pipelines, event streams, or WebFlux services. |
| **`OpenFeign`** | Declarative Interface | Spring Cloud. | Clean microservice contracts with minimal boilerplate and client load balancing. |

---

## 3. Maven dependencies (`pomxml`)

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-openfeign</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-loadbalancer</artifactId>
</dependency>
```

---

## 4. Declarative client with Spring Cloud OpenFeign

Enable Feign clients in your configuration or application class:

```java
package com.example;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.openfeign.EnableFeignClients;

@SpringBootApplication
@EnableFeignClients
public class OrderServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }
}
```

### Defining the Feign interface contract

```java
package com.example.client;

import com.example.dto.PaymentRequest;
import com.example.dto.PaymentResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

// name resolves to Eureka service ID or Kubernetes Service DNS; url is optional fallback
@FeignClient(name = "payment-service", path = "/api/v1/payments")
public interface PaymentClient {

    @PostMapping("/charge")
    PaymentResponse processPayment(@RequestBody PaymentRequest request);

    @GetMapping("/status/{paymentId}")
    PaymentResponse getPaymentStatus(@PathVariable("paymentId") String paymentId);
}
```

---

## 5. Propagating auth tokens custom `ErrorDecoder`

### 1. Request interceptor for security tracing context

When calling downstream microservices, the caller must propagate the incoming user's JWT Bearer token:

```java
package com.example.config;

import feign.RequestInterceptor;
import feign.RequestTemplate;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

@Configuration
public class FeignClientConfig {

    @Bean
    public RequestInterceptor bearerTokenRequestInterceptor() {
        return (RequestTemplate template) -> {
            ServletRequestAttributes attributes = 
                    (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            if (attributes != null) {
                HttpServletRequest request = attributes.getRequest();
                String authHeader = request.getHeader("Authorization");
                if (authHeader != null && !authHeader.isBlank()) {
                    template.header("Authorization", authHeader);
                }
            }
        };
    }
}
```

### 2. Custom `ErrorDecoder` for resilient error mapping

By default, Feign wraps all remote HTTP 4xx/5xx responses in a generic `FeignException`. A custom `ErrorDecoder` translates HTTP status codes into typed business domain exceptions:

```java
package com.example.client;

import com.example.exception.PaymentDeclinedException;
import com.example.exception.ResourceNotFoundException;
import feign.Response;
import feign.codec.ErrorDecoder;
import org.springframework.stereotype.Component;

@Component
public class CustomFeignErrorDecoder implements ErrorDecoder {

    private final ErrorDecoder defaultDecoder = new Default();

    @Override
    public Exception decode(String methodKey, Response response) {
        return switch (response.status()) {
            case 404 -> new ResourceNotFoundException("Requested downstream resource not found: " + methodKey);
            case 402, 400 -> new PaymentDeclinedException("Downstream payment rejected with status: " + response.status());
            case 503 -> new RuntimeException("Payment service temporarily unavailable. Triggering circuit breaker.");
            default -> defaultDecoder.decode(methodKey, response);
        };
    }
}
```

---

## 6. Modern synchronous `RestClient` alternative (Spring Boot 32)

If you prefer programmatic fluent APIs over declarative interfaces:

```java
@Service
public class CustomerServiceClient {

    private final RestClient restClient;

    public CustomerServiceClient(RestClient.Builder builder, @Value("${customer.service.url}") String baseUrl) {
        this.restClient = builder.baseUrl(baseUrl).build();
    }

    public CustomerDto getCustomerById(Long id) {
        return restClient.get()
                .uri("/api/v1/customers/{id}", id)
                .accept(MediaType.APPLICATION_JSON)
                .retrieve()
                .onStatus(HttpStatusCode::is4xxClientError, (req, resp) -> {
                    throw new ResourceNotFoundException("Customer " + id + " not found");
                })
                .body(CustomerDto.class);
    }
}
```

---

## 7. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Declarative Clients** | Spring Cloud OpenFeign requires separate dependency starter. | Native `@HttpExchange` HTTP Interface clients embedded directly in core Spring Framework. |
| **Virtual Threads** | Feign client threads run on platform threads unless using custom Apache HttpClient 5 pool. | Native virtual thread dispatchers for all outbound HTTP connections with non-blocking carrier threads. |
| **Load Balancing** | `spring-cloud-starter-loadbalancer` with round-robin and reactive service discovery. | Integrated client-side gRPC and HTTP/2 mesh balancing. |

---

## 8. Primary sources and further reading

- [Spring Cloud OpenFeign Official Reference](https://docs.spring.io/spring-cloud-openfeign/reference/), `@FeignClient`, configurations, and interceptors.
- [Spring Framework RestClient Reference](https://docs.spring.io/spring-framework/reference/integration/rest-clients.html#rest-restclient), Fluent synchronous client introduced in Spring 6.1.
- [Spring WebFlux WebClient Guide](https://docs.spring.io/spring-framework/reference/web/webflux-webclient.html).

---

## 9. Knowledge check and practice

??? question "Question 1: Why is `RestClient` preferred over `RestTemplate` for new Spring Boot 3.2+ applications?"
    **Answer**: `RestClient` provides a modern fluent API, better error handling (`onStatus`), and native integration with modern HTTP interfaces, whereas `RestTemplate` is in maintenance mode.

??? question "Question 2: What is the purpose of a Feign `RequestInterceptor` in a microservices cluster?"
    **Answer**: It automatically intercepts outbound Feign HTTP calls to inject required headers, such as JWT `Authorization` tokens or W3C `traceparent` distributed trace headers.

??? question "Question 3: How does a Feign `ErrorDecoder` improve error handling in microservices?"
    **Answer**: It intercepts remote HTTP 4xx and 5xx response codes and transforms them into typed domain exceptions instead of throwing generic `FeignException` objects.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0057: Monolith vs Microservices: System Design Principles**](0057-monolith-vs-microservices-system-design.md) | [**All Lessons**](index.md) | [ **0059: Service Registry & Discovery with Eureka**](0059-service-registry-discovery-eureka.md) |

🎉 **Lesson 0058 completed! Proceed to Lesson 0059 to master dynamic service registry and discovery with Spring Cloud Eureka.**
