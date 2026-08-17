---
icon: lucide/test-tube-2
---

# 0078: Integration Testing Reactive APIs with `WebTestClient` & Testcontainers

Testing reactive applications presents unique challenges. Because `Mono` and `Flux` execute asynchronously on Netty event loops, traditional assertions fail unless the test explicitly subscribes to the stream. Calling `.block()` in unit tests defeats the reactive model and can cause deadlocks.

Project Reactor provides **`StepVerifier`** for unit-testing reactive pipelines (including virtual time simulation), while Spring Boot provides **`WebTestClient`** for non-blocking integration testing of WebFlux controllers.

In this lesson, you will master testing reactive streams with `StepVerifier`, testing WebFlux endpoints using `@WebFluxTest` and `WebTestClient`, streaming validation, and integration testing with real R2DBC PostgreSQL Testcontainers.

---

## 1. Reactive Testing Architecture

``` mermaid
flowchart TD
    subgraph ReactiveUnitTests["1. Reactive Pipeline Unit Tests"]
        Pipeline["Reactive Service Pipeline (Mono / Flux)"]
        StepVerifierRunner["StepVerifier (reactor-test)"]
        
        StepVerifierRunner -->|Subscribes & Asserts Next Signals| Pipeline
        StepVerifierRunner -->|Asserts onComplete / onError| Pipeline
    end

    subgraph ReactiveHttpIntegration["2. WebFlux Integration Tests"]
        WebTestClientRunner["WebTestClient (Non-Blocking Test Harness)"]
        ControllerSlice["@WebFluxTest / @SpringBootTest"]
        R2dbcTestDB["PostgreSQL Testcontainer (@ServiceConnection R2DBC)"]
        
        WebTestClientRunner -->|HTTP GET/POST over Netty| ControllerSlice
        ControllerSlice -->|Reactive R2DBC queries| R2dbcTestDB
    end

    ReactiveUnitTests ~~~ ReactiveHttpIntegration
```

---

## 2. Maven Dependencies (`pom.xml`)

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>io.projectreactor</groupId>
    <artifactId>reactor-test</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-testcontainers</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>r2dbc</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>postgresql</artifactId>
    <scope>test</scope>
</dependency>
```

---

## 3. Unit Testing Streams with `StepVerifier`

`StepVerifier` verifies the exact sequence of items and terminal signals emitted by a Publisher:

```java
package com.example.service;

import com.example.dto.ProductResponse;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.test.StepVerifier;

import java.time.Duration;

class ProductServiceTest {

    @Test
    void testMonoPipeline() {
        Mono<String> usernameMono = Mono.just("alex_99")
                .map(String::toUpperCase);

        StepVerifier.create(usernameMono)
                .expectNext("ALEX_99")
                .verifyComplete();
    }

    @Test
    void testFluxStreamElementsAndError() {
        Flux<Integer> numberFlux = Flux.just(1, 2, 3, 0)
                .map(n -> 10 / n); // Throws ArithmeticException on 0

        StepVerifier.create(numberFlux)
                .expectNext(10)
                .expectNext(5)
                .expectNext(3)
                .expectError(ArithmeticException.class)
                .verify();
    }

    @Test
    void testVirtualTimeForDelayedStreams() {
        // Fast-forward 1 hour of delay instantly in test execution
        StepVerifier.withVirtualTime(() -> Flux.interval(Duration.ofMinutes(15)).take(3))
                .expectSubscription()
                .thenAwait(Duration.ofMinutes(45))
                .expectNext(0L, 1L, 2L)
                .verifyComplete();
    }
}
```

---

## 4. Testing WebFlux Endpoints with `WebTestClient`

`WebTestClient` is the reactive counterpart to `MockMvc`, providing non-blocking request execution and fluent JSON path assertions:

```java
package com.example.controller;

import com.example.dto.ProductRequest;
import com.example.dto.ProductResponse;
import com.example.service.ProductService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.WebFluxTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.MediaType;
import org.springframework.test.web.reactive.server.WebTestClient;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@WebFluxTest(controllers = ProductReactiveController.class)
class ProductControllerTest {

    @Autowired
    private WebTestClient webTestClient;

    @MockBean
    private ProductService productService;

    @Test
    void testGetProductById() {
        when(productService.findById(101L))
                .thenReturn(Mono.just(new ProductResponse(101L, "Laptop", 1200.0, "SKU-LAP")));

        webTestClient.get()
                .uri("/api/v1/products/101")
                .accept(MediaType.APPLICATION_JSON)
                .exchange()
                .expectStatus().isOk()
                .expectHeader().contentType(MediaType.APPLICATION_JSON)
                .expectBody()
                .jsonPath("$.id").isEqualTo(101)
                .jsonPath("$.name").isEqualTo("Laptop")
                .jsonPath("$.price").isEqualTo(1200.0);
    }

    @Test
    void testStreamEndpoint() {
        when(productService.findAllStream())
                .thenReturn(Flux.just(
                        new ProductResponse(1L, "Item 1", 10.0, "SKU-1"),
                        new ProductResponse(2L, "Item 2", 20.0, "SKU-2")
                ));

        webTestClient.get()
                .uri("/api/v1/products")
                .accept(MediaType.APPLICATION_NDJSON)
                .exchange()
                .expectStatus().isOk()
                .expectHeader().contentType(MediaType.APPLICATION_NDJSON)
                .returnResult(ProductResponse.class)
                .getResponseBody()
                .as(StepVerifier::create)
                .expectNextMatches(p -> p.name().equals("Item 1"))
                .expectNextMatches(p -> p.name().equals("Item 2"))
                .verifyComplete();
    }
}
```

---

## 5. End-to-End Testing with R2DBC Testcontainers

```java
package com.example.integration;

import com.example.model.Product;
import com.example.repository.ProductR2dbcRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.springframework.test.web.reactive.server.WebTestClient;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import reactor.test.StepVerifier;

import java.time.Instant;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@Testcontainers
class ReactivePersistenceIntegrationTest {

    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired
    private ProductR2dbcRepository productRepository;

    @Test
    void testRealR2dbcPersistence() {
        Product product = Product.builder()
                .name("Mechanical Keyboard")
                .price(150.0)
                .sku("SKU-KB-01")
                .createdAt(Instant.now())
                .build();

        productRepository.save(product)
                .flatMap(saved -> productRepository.findById(saved.getId()))
                .as(StepVerifier::create)
                .expectNextMatches(p -> p.getName().equals("Mechanical Keyboard") && p.getPrice() == 150.0)
                .verifyComplete();
    }
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Mocking in WebFlux** | Transitioning from `@MockBean` to `@MockitoBean` (Spring 6.2+). | Native reflection-free mock injection for GraalVM test targets. |
| **R2DBC Testcontainers** | Automatic `@ServiceConnection` dynamic R2DBC URL injection. | Instant R2DBC schema snapshot restoring in < 50ms per test. |
| **WebTestClient** | HTTP/1.1 and HTTP/2 test client harness. | Native HTTP/3 WebTransport and SSE duplex stream assertions. |

---

## 7. Primary Sources & Further Reading

- [Testing Reactive Streams with StepVerifier](https://projectreactor.io/docs/core/release/reference/#testing).
- [Spring WebFlux WebTestClient Documentation](https://docs.spring.io/spring-framework/reference/testing/webtestclient.html).
- [Spring Boot Testcontainers R2DBC Guide](https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.testing.testcontainers).

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: Why is calling `.block()` in reactive unit tests considered an anti-pattern?"
    **Answer**: It violates the non-blocking execution model, can trigger deadlocks when executed on event loop threads, and fails to verify asynchronous signals properly.

??? question "Question 2: What is the benefit of `StepVerifier.withVirtualTime()`?"
    **Answer**: It simulates clock advancement in memory, allowing tests with long delays (e.g., hours or days) to execute completely in milliseconds.

??? question "Question 3: How does `WebTestClient` verify Server-Sent Events or NDJSON streams?"
    **Answer**: By using `.returnResult(Class).getResponseBody()` and piping the resulting reactive `Flux` directly into `StepVerifier` for signal-by-signal assertions.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0077: Reactive Backpressure: Bounded flatMap & Buffers**](0077-reactive-backpressure-flatmap-buffer-strategies.md) | [**All Lessons**](index.md) | [➡️ **0079: Spring AI: LLM Chat Clients & Prompts**](0079-spring-ai-llm-chatclient-prompts.md) |

🎉 **Lesson 0078 completed! Proceed to Lesson 0079 to start exploring Spring AI, LLM ChatClients, and prompt engineering.**
