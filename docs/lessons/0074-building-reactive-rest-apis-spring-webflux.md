---
icon: lucide/zap
---

# 0074: Building Reactive REST APIs with Spring WebFlux

Spring WebFlux offers two distinct programming models for building non-blocking HTTP services:
1. **Annotated Controllers**: The familiar Spring MVC-style annotations (`@RestController`, `@GetMapping`, `@PostMapping`), adapted to return `Mono<T>` and `Flux<T>`.
2. **Functional Endpoints (Router Functions)**: A lightweight, lambda-driven model using `RouterFunction` and `HandlerFunction` that provides explicit route definition and minimal reflection overhead.

In this lesson, you will master building reactive REST APIs using both models, handling request body validation, returning streaming JSON, and handling exceptions with reactive `ProblemDetails`.

---

## 1. WebFlux Request Processing Pipeline

``` mermaid
flowchart TD
    subgraph ClientTier["HTTP Client"]
        ClientReq["HTTP Request (GET /api/v1/products, POST /api/v1/orders)"]
    end

    subgraph WebFluxEngine["Spring WebFlux (Netty Reactor Engine)"]
        HttpHandler["HttpHandler (Netty Bridge)"]
        WebHandler["DispatcherHandler (Reactive Dispatcher)"]
        
        subgraph HandlerChoices["Handler Resolution"]
            AnnotatedCtrl["Annotated @RestController"]
            RouterFn["Functional RouterFunction & HandlerFunction"]
        end
        
        FilterPipeline["WebFilter Chain (Security, Tracing, CORS)"]
        
        HttpHandler --> FilterPipeline
        FilterPipeline --> WebHandler
        WebHandler --> AnnotatedCtrl
        WebHandler --> RouterFn
    end

    subgraph ReactiveServiceLayer["Reactive Domain Services"]
        ProductService["ProductService (returns Mono / Flux)"]
    end

    ClientReq --> HttpHandler
    AnnotatedCtrl --> ProductService
    RouterFn --> ProductService
    ProductService -.->|Emits Reactive Event Stream| ClientReq
```

---

## 2. Model 1: Annotated Reactive Controllers

```java
package com.example.controller;

import com.example.dto.ProductRequest;
import com.example.dto.ProductResponse;
import com.example.service.ProductService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@RestController
@RequestMapping("/api/v1/products")
@RequiredArgsConstructor
public class ProductReactiveController {

    private final ProductService productService;

    @GetMapping("/{id}")
    public Mono<ResponseEntity<ProductResponse>> getProductById(@PathVariable Long id) {
        return productService.findById(id)
                .map(ResponseEntity::ok)
                .defaultIfEmpty(ResponseEntity.notFound().build());
    }

    /**
     * Streams items as Newline Delimited JSON (NDJSON) as they are produced from DB
     */
    @GetMapping(produces = MediaType.APPLICATION_NDJSON_VALUE)
    public Flux<ProductResponse> streamAllProducts() {
        return productService.findAllStream();
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public Mono<ProductResponse> createProduct(@Valid @RequestBody Mono<ProductRequest> requestMono) {
        // Defer request body resolution reactively
        return requestMono.flatMap(productService::saveProduct);
    }
}
```

---

## 3. Model 2: Functional Router Functions

Functional endpoints decouple routing configuration from request processing logic:

### 1. Handler Function

```java
package com.example.handler;

import com.example.dto.ProductRequest;
import com.example.dto.ProductResponse;
import com.example.service.ProductService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.server.ServerRequest;
import org.springframework.web.reactive.function.server.ServerResponse;
import reactor.core.publisher.Mono;

import java.net.URI;

@Component
@RequiredArgsConstructor
public class ProductHandler {

    private final ProductService productService;

    public Mono<ServerResponse> getProduct(ServerRequest request) {
        Long id = Long.valueOf(request.pathVariable("id"));
        return productService.findById(id)
                .flatMap(product -> ServerResponse.ok()
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue(product))
                .switchIfEmpty(ServerResponse.notFound().build());
    }

    public Mono<ServerResponse> createProduct(ServerRequest request) {
        return request.bodyToMono(ProductRequest.class)
                .flatMap(productService::saveProduct)
                .flatMap(saved -> ServerResponse.created(URI.create("/api/v2/products/" + saved.id()))
                        .contentType(MediaType.APPLICATION_JSON)
                        .bodyValue(saved));
    }
}
```

### 2. Router Function

```java
package com.example.config;

import com.example.handler.ProductHandler;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.server.RouterFunction;
import org.springframework.web.reactive.function.server.ServerResponse;

import static org.springframework.web.reactive.function.server.RequestPredicates.accept;
import static org.springframework.web.reactive.function.server.RouterFunctions.route;

@Configuration
public class ProductRouterConfig {

    @Bean
    public RouterFunction<ServerResponse> productRoutes(ProductHandler handler) {
        return route()
                .path("/api/v2/products", builder -> builder
                        .GET("/{id}", accept(MediaType.APPLICATION_JSON), handler::getProduct)
                        .POST("", accept(MediaType.APPLICATION_JSON), handler::createProduct)
                )
                .build();
    }
}
```

---

## 4. Reactive Global Exception Handling

In WebFlux, handle exceptions globally using `@RestControllerAdvice` with RFC 7807/9457 `ProblemDetails`:

```java
package com.example.exception;

import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetails;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.bind.support.WebExchangeBindException;
import reactor.core.publisher.Mono;

import java.net.URI;
import java.time.Instant;
import java.util.List;

@RestControllerAdvice
public class ReactiveGlobalExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public Mono<ResponseEntity<ProblemDetails>> handleNotFound(ResourceNotFoundException ex) {
        ProblemDetails problem = ProblemDetails.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        problem.setTitle("Resource Not Found");
        problem.setType(URI.create("https://api.example.com/errors/not-found"));
        problem.setProperty("timestamp", Instant.now());
        return Mono.just(ResponseEntity.status(HttpStatus.NOT_FOUND).body(problem));
    }

    @ExceptionHandler(WebExchangeBindException.class)
    public Mono<ResponseEntity<ProblemDetails>> handleValidation(WebExchangeBindException ex) {
        ProblemDetails problem = ProblemDetails.forStatusAndDetail(HttpStatus.BAD_REQUEST, "Validation failed");
        List<String> errors = ex.getFieldErrors().stream()
                .map(err -> err.getField() + ": " + err.getDefaultMessage())
                .toList();
        problem.setProperty("errors", errors);
        return Mono.just(ResponseEntity.badRequest().body(problem));
    }
}
```

---

## 5. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Error Handling** | RFC 7807/9457 `ProblemDetails` integrated in WebFlux and MVC. | Native compiler-checked error schema contracts and client SDK generation. |
| **Router DSL** | Functional Java Builder API (`route().GET(...).build()`). | Kotlin / Java fluent pattern-matching routing macros. |
| **GraalVM Reflection** | Requires `@RegisterReflectionForBinding` for Functional handlers. | Zero-reflection GraalVM reachability for all RouterFunction routes. |

---

## 6. Primary Sources & Further Reading

- [Spring WebFlux Annotated Controllers](https://docs.spring.io/spring-framework/reference/web/webflux/controller.html).
- [Spring WebFlux Functional Endpoints](https://docs.spring.io/spring-framework/reference/web/webflux/functional.html).
- [RFC 9457: Problem Details for HTTP APIs](https://datatracker.ietf.org/doc/html/rfc9457).

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the main advantage of Functional Endpoints (`RouterFunction`) over Annotated Controllers?"
    **Answer**: Functional endpoints provide explicit, compile-time routing without reflection, annotation scanning overhead, or framework proxy generation.

??? question "Question 2: Why is `MediaType.APPLICATION_NDJSON_VALUE` used when streaming collections with WebFlux?"
    **Answer**: Newline Delimited JSON streams individual JSON objects as discrete lines over a persistent HTTP connection as soon as they become available.

??? question "Question 3: How does `@RequestBody Mono<RequestDto>` benefit WebFlux controllers?"
    **Answer**: It defers decoding and reading the incoming HTTP request body until downstream reactive subscribers explicitly demand data.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0073: Project Reactor: Mono, Flux & Schedulers**](0073-project-reactor-mono-flux-schedulers.md) | [**All Lessons**](index.md) | [➡️ **0075: Non-Blocking Persistence with R2DBC & Reactive Redis**](0075-nonblocking-persistence-r2dbc-reactive-redis.md) |

🎉 **Lesson 0074 completed! Proceed to Lesson 0075 to master end-to-end non-blocking persistence with R2DBC and Reactive Redis.**
