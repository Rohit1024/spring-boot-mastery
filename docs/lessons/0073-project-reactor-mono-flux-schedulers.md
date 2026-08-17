---
icon: lucide/workflow
---

# 0073: Project Reactor Fundamentals: Mono, Flux, Schedulers & Pipelines

Spring WebFlux is built on **Project Reactor**, a 4th-generation Reactive library based on the Reactive Streams specification. In Reactor, data flows through functional, declarative processing pipelines.

A fundamental axiom in reactive programming is:
> **"Nothing happens until you subscribe!"**

In this lesson, you will master the two primary reactive types (`Mono` and `Flux`), essential transformation and combination operators (`map`, `flatMap`, `zip`), error handling strategies, and managing thread execution using `Schedulers`.

---

## 1. Core Reactive Publishers: `Mono` vs `Flux`

``` mermaid
flowchart TD
    subgraph MonoStream["Mono<T>: 0 or 1 Element Stream"]
        M1["Subscription Initiated"]
        M2["Emits single item T e.g. User or Empty"]
        M3["onComplete / onError Signal"]
        M1 --> M2 --> M3
    end

    subgraph FluxStream["Flux<T>: 0 to N Elements (or Unbounded Stream)"]
        F1["Subscription Initiated"]
        F2["onNext(item 1)"]
        F3["onNext(item 2)"]
        F4["onNext(item N)..."]
        F5["onComplete / onError Signal"]
        F1 --> F2 --> F3 --> F4 --> F5
    end

    MonoStream ~~~ FluxStream
```

---

## 2. Transforming Reactive Streams: `map` vs `flatMap`

| Operator | Signature | Behavior | Use Case |
| :--- | :--- | :--- | :--- |
| **`map`** | `T -> R` (Synchronous 1:1) | Synchronously transforms each item in-memory. | Property extraction, math, DTO conversion (`user -> UserDto`). |
| **`flatMap`** | `T -> Mono<R>` / `Flux<R>` | Asynchronously flattens and merges nested publishers in parallel. | Making asynchronous database queries or outbound HTTP calls per item. |
| **`concatMap`** | `T -> Publisher<R>` | Like `flatMap`, but strictly **preserves original item ordering** sequentially. | Sequential processing where order is critical. |

```java
// 1. Synchronous map: Extracting uppercase name
Mono<String> usernameMono = Mono.just(new User(101L, "Alice"))
        .map(User::getName)
        .map(String::toUpperCase);

// 2. Asynchronous flatMap: Calling remote service per order
Flux<PaymentStatus> paymentStatuses = Flux.fromIterable(orderList)
        .flatMap(order -> paymentClient.chargeOrderAsync(order)); // Non-blocking parallel calls
```

---

## 3. Combining Streams: `zip`, `merge` & `switchIfEmpty`

```java
// 1. Zip: Combining results from two independent services concurrently
Mono<UserProfileDto> profileMono = Mono.zip(
        userService.findUserById(101L),       // Fetches in parallel
        orderService.findRecentOrders(101L)   // Fetches in parallel
).map(tuple -> {
    User user = tuple.getT1();
    List<Order> orders = tuple.getT2();
    return new UserProfileDto(user, orders);
});

// 2. Fallback: switchIfEmpty (Checking Cache then falling back to Database)
Mono<Product> productMono = redisReactiveCache.getProduct(productId)
        .switchIfEmpty(databaseRepository.findById(productId));
```

---

## 4. Error Handling in Reactive Pipelines

In reactive streams, exceptions are first-class terminal signals propagated via `onError`. Reactor provides functional recovery operators:

```java
public Mono<OrderResponse> processOrder(OrderRequest request) {
    return paymentService.chargeCard(request)
            // 1. Fallback to default value on failure
            .onErrorReturn(new PaymentResponse("DEGRADED_FALLBACK"))
            
            // 2. Or resume with alternate reactive stream
            .onErrorResume(PaymentGatewayException.class, ex -> {
                log.warn("Primary gateway failed, trying backup provider...", ex);
                return backupPaymentService.chargeCard(request);
            })
            
            // 3. Transform low-level exception to domain exception
            .onErrorMap(IOException.class, ex -> new ServiceUnavailableException("Network timeout", ex))
            
            // 4. Automatic retry with exponential backoff
            .retryWhen(Retry.backoff(3, Duration.ofMillis(500)).jitter(0.5))
            
            .map(resp -> new OrderResponse(request.orderId(), resp.status()));
}
```

---

## 5. Thread Scheduling: `subscribeOn` vs `publishOn`

Reactor decouples execution from specific thread pools using `Schedulers`:
- **`Schedulers.parallel()`**: Optimized for CPU-intensive computation (pool sized to CPU cores).
- **`Schedulers.boundedElastic()`**: Designed for wrapping legacy blocking I/O (dynamically creates worker threads and queues tasks).
- **`Schedulers.immediate()`**: Executes on the current calling thread.

``` mermaid
flowchart TD
    subgraph ExecutionTimeline["publishOn vs subscribeOn Thread Transition"]
        S1["Source Publisher: Mono.just('file.txt')"]
        S2["subscribeOn: Schedulers.boundedElastic (Upstream read happens on worker thread)"]
        S3["publishOn: Schedulers.parallel (Downstream execution switches to parallel thread)"]
        S4["CPU Computation: Hash / Encrypt"]
        
        S1 --> S2 --> S3 --> S4
    end
```

```java
// Safely offloading legacy blocking call to boundedElastic scheduler
public Mono<byte[]> readLegacyFile(String path) {
    return Mono.fromCallable(() -> Files.readAllBytes(Paths.get(path))) // Blocking I/O
            .subscribeOn(Schedulers.boundedElastic())                   // Runs off-event-loop
            .publishOn(Schedulers.parallel())                          // Switches to CPU thread
            .map(this::calculateChecksum);
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Reactor Core Version** | Reactor Core 3.6+ with Java 17/21 baseline. | Reactor Core 3.7 / 4.x with native Vector API optimizations. |
| **Virtual Thread Scheduler** | Custom `Schedulers.fromExecutor(Executors.newVirtualThreadPerTaskExecutor())`. | Native `Schedulers.virtual()` integration replacing boundedElastic for blocking bridges. |
| **Context Propagation** | Micrometer Context Propagation library for MDC tracing. | Built-in JVM Scoped Values (`ScopedValue`) with zero ThreadLocal wrapping. |

---

## 7. Primary Sources & Further Reading

- [Project Reactor Official Reference Guide](https://projectreactor.io/docs/core/release/reference/) — Mono, Flux, and Operators.
- [Flight of the Flux: A Guide to Reactive Operators](https://spring.io/blog/2019/12/13/flight-of-the-flux-1-assembly-vs-subscription).
- [Reactive Streams Java API Reference](https://www.reactive-streams.org/).

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the semantic difference between `Mono<T>` and `Flux<T>`?"
    **Answer**: `Mono<T>` emits 0 or 1 element (or error), while `Flux<T>` emits an asynchronous sequence of 0 to N elements (or an unbounded stream).

??? question "Question 2: What is the difference between `map` and `flatMap` in Project Reactor?"
    **Answer**: `map` performs a synchronous 1:1 transformation in-memory, while `flatMap` transforms elements into asynchronous publishers and merges them concurrently.

??? question "Question 3: When should `Schedulers.boundedElastic()` be utilized?"
    **Answer**: When bridging legacy blocking I/O (like JDBC queries or file system reads) into a reactive pipeline to prevent freezing the Netty event loop threads.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0072: Blocking vs Non-Blocking I/O: The Reactive Paradigm**](0072-blocking-vs-nonblocking-reactive-paradigm.md) | [**All Lessons**](index.md) | [➡️ **0074: Building Reactive REST APIs with Spring WebFlux**](0074-building-reactive-rest-apis-spring-webflux.md) |

🎉 **Lesson 0073 completed! Proceed to Lesson 0074 to build production-grade reactive REST controllers and functional endpoints with WebFlux.**
