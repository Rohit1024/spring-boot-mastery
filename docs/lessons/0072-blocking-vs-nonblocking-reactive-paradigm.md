---
icon: lucide/cpu
---

# 0072: Blocking vs Non-Blocking I/O: The Reactive Paradigm at Scale

In traditional Servlet-based architectures (Spring MVC with Apache Tomcat), requests operate on a **Thread-per-Request** model. When 200 concurrent requests execute blocking I/O (such as waiting for a slow PostgreSQL query or a 3-second third-party REST call), 200 operating system threads sit idle, consuming ~1MB of stack memory each and wasting CPU cycles on heavy OS context switching.

The **Reactive Streams Paradigm** (Spring WebFlux with Eclipse Netty) runs on an asynchronous, **Event Loop model**. A tiny pool of worker threads (matching CPU core count) handles tens of thousands of concurrent client connections without ever blocking.

In this lesson, you will master the mechanics of the Netty Event Loop vs Tomcat Thread Pool, the Reactive Streams specification (Publisher, Subscriber, Subscription), and understand when to choose WebFlux vs Spring MVC with Virtual Threads.

---

## 1. Thread-per-Request vs Event Loop Architecture

``` mermaid
flowchart TD
    subgraph TraditionalMVC["Traditional Spring MVC (Thread-per-Request on Tomcat)"]
        Req1["Request 1"] --> Thread1["Thread 1 (Blocked on DB I/O - 1MB RAM)"]
        Req2["Request 2"] --> Thread2["Thread 2 (Blocked on Payment I/O - 1MB RAM)"]
        Req3["Request 3"] --> Thread3["Thread 3 (Blocked on Disk I/O - 1MB RAM)"]
        ReqN["Request 500"] --> QueuePool["Thread Pool Exhaustion (HTTP 503 / Latency Spike)"]
    end

    subgraph ReactiveWebFlux["Reactive Spring WebFlux (Event Loop on Netty)"]
        EventLoop["Netty Event Loop (1 Worker Thread per CPU Core)"]
        SocketChannel["Non-Blocking Linux epoll / kqueue Socket Channels"]
        
        R1["Request 1"] --> SocketChannel
        R2["Request 2"] --> SocketChannel
        R3["Request 3"] --> SocketChannel
        RN["Request 10,000"] --> SocketChannel
        
        SocketChannel --> EventLoop
        EventLoop -->|Register Callback & Free Thread| ReactiveDB["Non-Blocking Driver (R2DBC / WebClient)"]
        ReactiveDB -.->|I/O Event Ready: Resume Pipeline| EventLoop
    end

    TraditionalMVC ~~~ ReactiveWebFlux
```

---

## 2. The Reactive Streams Specification

Reactive programming in Java is governed by the official **Reactive Streams Specification** (Java 9 `java.util.concurrent.Flow`), defined by 4 foundational interfaces:

```java
// 1. Publisher: Emits a sequence of items to registered subscribers
public interface Publisher<T> {
    void subscribe(Subscriber<? super T> s);
}

// 2. Subscriber: Receives items and signals from a publisher
public interface Subscriber<T> {
    void onSubscribe(Subscription s);
    void onNext(T t);          // Received next data item
    void onError(Throwable t);  // Terminated with failure
    void onComplete();          // Successfully completed stream
}

// 3. Subscription: Manages the lifecycle link between Publisher and Subscriber
public interface Subscription {
    void request(long n);       // 🔒 Demand-driven Backpressure: request n items
    void cancel();              // Cancel stream consumption
}

// 4. Processor: Acts as both a Subscriber and Publisher for pipeline transformation
public interface Processor<T, R> extends Subscriber<T>, Publisher<R> {}
```

---

## 3. Spring MVC (with Virtual Threads) vs Spring WebFlux

With the introduction of Java 21 Virtual Threads (Project Loom), architects often ask: *Do we still need Spring WebFlux?*

| Feature | Spring MVC + Platform Threads | Spring MVC + Virtual Threads (Java 21) | Spring WebFlux (Netty Event Loop) |
| :--- | :--- | :--- | :--- |
| **I/O Model** | Blocking OS Threads. | Blocking Virtual Threads (Carrier unmounts on I/O). | Non-blocking Event Loop (`epoll`/`kqueue`). |
| **Programming Style** | Imperative / Synchronous (`return user`). | Imperative / Synchronous (`return user`). | Functional / Declarative (`Mono<User>`, `Flux<User>`). |
| **Memory per Connection** | High (~1MB per thread stack). | Low (~1KB per virtual thread). | Ultra-Low (~few bytes per socket buffer). |
| **Streaming / SSE** | Limited (Thread held during stream). | Capable, but uses thread resources. | Native first-class reactive streaming. |
| **Ecosystem Compatibility** | 100% (JDBC, Hibernate, Feign). | 98% (Avoid `synchronized` pinning). | Requires non-blocking drivers (R2DBC, Reactive Redis). |

> [!TIP]
> **Architectural Guidance**:
> - Use **Spring MVC with Virtual Threads** for standard enterprise REST APIs with relational databases (JPA/Hibernate) where sequential imperative code is easiest to maintain.
> - Use **Spring WebFlux** for high-scale API Gateways, real-time Server-Sent Events (SSE) / WebSocket streams, telemetry ingestion, and low-latency microservice proxies.

---

## 4. The Golden Rule of Reactive Programming

> [!CAUTION]
> **NEVER BLOCK THE EVENT LOOP**: In a Netty event loop with only 8 worker threads, executing a single blocking call (`Thread.sleep()`, `jdbcTemplate.query()`, `restTemplate.getForObject()`) halts 12.5% of your entire server capacity. If 8 requests block simultaneously, the whole server freezes.

```java
// ❌ CRITICAL ANTI-PATTERN: Blocking inside WebFlux
@GetMapping("/users/{id}")
public Mono<UserDto> getUser(@PathVariable Long id) {
    // BLOCKS Netty Event Loop Thread!
    User user = blockingJpaRepository.findById(id).orElseThrow(); 
    return Mono.just(UserDto.from(user));
}

// ✅ CORRECT: Pure Non-Blocking Reactive Pipeline
@GetMapping("/users/{id}")
public Mono<UserDto> getUserReactive(@PathVariable Long id) {
    return reactiveR2dbcRepository.findById(id)
            .map(UserDto::from)
            .switchIfEmpty(Mono.error(new ResourceNotFoundException("User not found")));
}
```

---

## 5. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Reactive Runtime** | Reactor Netty 1.1+ with JDK 17/21 baseline. | Native HTTP/3 and QUIC transport protocol support on Netty 5.x. |
| **Context Propagation** | Project Reactor Context with Micrometer Tracing hooks. | Native Scoped Values (`ScopedValue`) carrying tracing context through reactive operators. |
| **GraalVM Native Images** | Out-of-the-box AOT compilation with sub-20ms cold starts on WebFlux. | Instantaneous micro-runtimes consuming < 25MB RAM under 10k connections. |

---

## 6. Primary Sources & Further Reading

- [Reactive Streams Standard Specification](https://www.reactive-streams.org/).
- [Spring Framework WebFlux Reference](https://docs.spring.io/spring-framework/reference/web/webflux.html).
- [Project Reactor Official Reference Guide](https://projectreactor.io/docs/core/release/reference/).

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the primary difference in thread allocation between Spring MVC and Spring WebFlux?"
    **Answer**: Spring MVC allocates a dedicated thread per HTTP request (typically 200 max), while WebFlux uses a fixed non-blocking Netty event loop (1 worker thread per CPU core) to handle thousands of requests.

??? question "Question 2: What happens if a blocking JDBC query is executed inside a Spring WebFlux controller?"
    **Answer**: It freezes one of the few Netty event loop threads, quickly exhausting the event loop and causing the entire server to stop processing concurrent traffic.

??? question "Question 3: What is the role of the `Subscription` interface in the Reactive Streams specification?"
    **Answer**: It mediates the relationship between Publisher and Subscriber, allowing the Subscriber to request a specific number of items (`request(n)`) to enforce backpressure.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0071: Cloud CI/CD: AWS CodePipeline & Beanstalk**](0071-cloud-cicd-aws-codepipeline-beanstalk.md) | [**All Lessons**](index.md) | [➡️ **0073: Project Reactor: Mono, Flux & Schedulers**](0073-project-reactor-mono-flux-schedulers.md) |

🎉 **Lesson 0072 completed! Proceed to Lesson 0073 to master Project Reactor core types (`Mono`, `Flux`), transformation operators, and Schedulers.**
