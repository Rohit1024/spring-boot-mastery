---
icon: lucide/shield-check
---

# 0060: API Gateway routing and security with Spring Cloud Gateway

Exposing internal microservices directly to external mobile and web clients introduces serious security risks, tight coupling to internal URLs, and fragmented cross-cutting concerns (authentication, CORS, rate limiting, logging).

An **API Gateway** acts as the single, hardened reverse-proxy entry point for all external traffic. **Spring Cloud Gateway** is built on top of Spring WebFlux, Project Reactor, and Netty, delivering high-throughput, non-blocking routing, dynamic path rewrites, and security filter chains.

In this lesson, you will master route predicates, gateway filter factories, dynamic Eureka load-balanced routing (`lb://`), and implementing reactive authentication filters.

---

## 1. Spring Cloud gateway architecture

``` mermaid
flowchart TD
    subgraph Clients["External Clients"]
        WebClient["SPA Web Application"]
        MobileApp["Mobile App (iOS / Android)"]
    end

    subgraph GatewayCore["Spring Cloud Gateway (Reactive Netty on Port 8080)"]
        HandlerMapping["RoutePredicateHandlerMapping"]
        
        subgraph FilterPipeline["Gateway Filter Chain"]
            GlobalAuthFilter["1. Global JWT Authentication Filter"]
            RateLimitFilter["2. Redis RequestRateLimiter Filter"]
            PathRewriteFilter["3. RewritePath Filter (/api/v1/orders/** -> /**)"]
        end
        
        LoadBalancerClient["Spring Cloud LoadBalancer (lb://)"]
    end

    subgraph BackendServices["Internal Microservices (Private VPC)"]
        OrderService["Order Service (lb://ORDER-SERVICE)"]
        PaymentService["Payment Service (lb://PAYMENT-SERVICE)"]
        CustomerService["Customer Service (lb://CUSTOMER-SERVICE)"]
    end

    WebClient --> HandlerMapping
    MobileApp --> HandlerMapping
    HandlerMapping --> GlobalAuthFilter
    GlobalAuthFilter --> RateLimitFilter
    RateLimitFilter --> PathRewriteFilter
    PathRewriteFilter --> LoadBalancerClient
    
    LoadBalancerClient -->|Dispatched to instance| OrderService
    LoadBalancerClient -->|Dispatched to instance| PaymentService
    LoadBalancerClient -->|Dispatched to instance| CustomerService
```

---

## 2. Maven dependencies (`pomxml`)

> [!CAUTION]
> **No Spring MVC Starter**: Spring Cloud Gateway is built on **Spring WebFlux and Netty**. Do not include `spring-boot-starter-web` (Tomcat) in the Gateway project, as it conflicts with the reactive Netty runtime.

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-gateway</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-client</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-loadbalancer</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis-reactive</artifactId>
</dependency>
```

---

## 3. Declarative route configuration (`applicationyml`)

Configure routing rules, path predicates, rewrites, and load balancing:

```yaml
server:
  port: 8080

spring:
  application:
    name: api-gateway
  cloud:
    gateway:
      routes:
        # Route 1: Order Service with Path Rewriting and Header Injection
        - id: order-service-route
          uri: lb://ORDER-SERVICE
          predicates:
            - Path=/api/v1/orders/**
            - Method=GET,POST,PUT,DELETE
          filters:
            - RewritePath=/api/v1/orders/(?<segment>.*), /api/orders/${segment}
            - AddResponseHeader=X-Gateway-Processed-By, api-gateway-v1

        # Route 2: Payment Service with Token Relay
        - id: payment-service-route
          uri: lb://PAYMENT-SERVICE
          predicates:
            - Path=/api/v1/payments/**
          filters:
            - TokenRelay= # Automatically relays incoming OAuth2 Bearer token downstream

      # Global CORS configuration
      globalcors:
        cors-configurations:
          '[/**]':
            allowedOrigins: "https://app.example.com"
            allowedMethods:
              - GET
              - POST
              - PUT
              - DELETE
              - OPTIONS
            allowedHeaders: "*"
            allowCredentials: true
```

---

## 4. Reactive global JWT authentication filter

A `GlobalFilter` executes on every request passing through the gateway without needing explicit attachment in YAML:

```java
package com.example.gateway.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.List;

@Slf4j
@Component
public class JwtAuthenticationGlobalFilter implements GlobalFilter, Ordered {

    // Public endpoints that do not require authorization
    private static final List<String> OPEN_ENDPOINTS = List.of(
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/actuator/health"
    );

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String path = request.getURI().getPath();

        if (isOpenEndpoint(path)) {
            return chain.filter(exchange);
        }

        // Validate presence of Authorization header
        if (!request.getHeaders().containsKey(HttpHeaders.AUTHORIZATION)) {
            return onError(exchange, "Missing Authorization Header", HttpStatus.UNAUTHORIZED);
        }

        String authHeader = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            return onError(exchange, "Invalid Authorization Header Format", HttpStatus.UNAUTHORIZED);
        }

        String token = authHeader.substring(7);

        try {
            // Validate JWT token & extract claims (e.g. userId, tenantId)
            String userId = validateAndExtractUserId(token);

            // Mutate request to inject verified identity headers for downstream services
            ServerHttpRequest mutatedRequest = request.mutate()
                    .header("X-User-Id", userId)
                    .build();

            return chain.filter(exchange.mutate().request(mutatedRequest).build());

        } catch (Exception e) {
            log.error("JWT validation error on path: {}", path, e);
            return onError(exchange, "Unauthorized: Invalid or Expired Token", HttpStatus.UNAUTHORIZED);
        }
    }

    private boolean isOpenEndpoint(String path) {
        return OPEN_ENDPOINTS.stream().anyMatch(path::startsWith);
    }

    private Mono<Void> onError(ServerWebExchange exchange, String err, HttpStatus httpStatus) {
        ServerHttpResponse response = exchange.getResponse();
        response.setStatusCode(httpStatus);
        return response.setComplete();
    }

    private String validateAndExtractUserId(String token) {
        // Validation logic using Nimbus-JOSE / JJWT library
        return "usr-9941";
    }

    @Override
    public int getOrder() {
        return -100; // High priority in filter chain
    }
}
```

---

## 5. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Gateway Flavors** | Spring Cloud Gateway Reactive (WebFlux) and new Servlet-based Gateway MVC. | Unified multi-engine gateway architecture using Project Loom Virtual Threads for MVC. |
| **Observability** | Gateway metrics automatically exported to Prometheus via Micrometer. | Native OpenTelemetry distributed span propagation and W3C Baggage carrier injection. |
| **Security Interoperability** | TokenRelayGatewayFilterFactory with Spring Security 6 OAuth2 Resource Server. | Built-in zero-trust cryptographic mutual TLS (mTLS) gateway routing tunnels. |

---

## 6. Primary sources and further reading

- [Spring Cloud Gateway Official Reference Guide](https://docs.spring.io/spring-cloud-gateway/reference/), Predicates, Filter Factories, and Global Filters.
- [Spring Cloud Gateway Server MVC Documentation](https://docs.spring.io/spring-cloud-gateway/reference/spring-cloud-gateway-server-mvc.html).
- [Project Reactor Core Documentation](https://projectreactor.io/docs/core/release/reference/).

---

## 7. Knowledge check and practice

??? question "Question 1: Why should `spring-boot-starter-web` NOT be added as a dependency in Spring Cloud Gateway projects?"
    **Answer**: Spring Cloud Gateway is built on the reactive Spring WebFlux and Netty engine; including Tomcat (`spring-boot-starter-web`) introduces classpath conflicts and breaks the non-blocking event loop.

??? question "Question 2: What is the difference between a Route Predicate and a Gateway Filter?"
    **Answer**: A Predicate evaluates incoming HTTP request attributes to decide if a route matches, while a Filter inspects and modifies the request or response before and after routing.

??? question "Question 3: How does the `lb://` URI scheme function in Spring Cloud Gateway routes?"
    **Answer**: It instructs Spring Cloud LoadBalancer to look up the target service name in the Service Registry (e.g. Eureka) and dynamically route traffic to a healthy instance.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0059: Service Registry & Discovery with Eureka**](0059-service-registry-discovery-eureka.md) | [**All Lessons**](index.md) | [ **0061: Centralized Config Server & Dynamic Bus Refresh**](0061-centralized-config-server-bus-refresh.md) |

🎉 **Lesson 0060 completed! Proceed to Lesson 0061 to master centralized externalized configuration with Spring Cloud Config Server and Spring Cloud Bus.**
