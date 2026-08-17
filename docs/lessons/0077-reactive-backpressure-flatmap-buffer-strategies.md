---
icon: lucide/gauge
---

# 0077: Reactive Backpressure Handling: Bounded `flatMap` & Buffer Strategies

In high-volume streaming systems, a **Fast Publisher** can easily emit 100,000 items per second while a **Slow Downstream Consumer** (such as a database writer or third-party payment API) can only process 500 items per second.

Without backpressure, unconsumed items accumulate in JVM heap memory, causing latency spikes, garbage collection freezes, and fatal `OutOfMemoryError` (OOM) crashes.

**Backpressure** is the feedback mechanism defined by the Reactive Streams specification where consumers explicitly signal their capacity to publishers via `Subscription.request(n)`.

In this lesson, you will master handling overflow scenarios with Project Reactor backpressure strategies (`onBackpressureBuffer`, `onBackpressureDrop`, `onBackpressureLatest`), bounding `flatMap` concurrency, and tuning stream prefetching with `limitRate`.

---

## 1. Fast Producer vs Slow Consumer with Backpressure

``` mermaid
flowchart TD
    subgraph FastProducer["Fast Publisher (Kafka / WebSocket Ingestion)"]
        StreamGen["Event Stream (10,000 events/sec)"]
    end

    subgraph BackpressureGate["Reactive Backpressure Control Layer"]
        DemandSignal["Subscription.request(n): Demand Signal"]
        BufferPolicy["onBackpressureBuffer(max=1000, DROP_OLDEST)"]
        BoundedFlatMap["flatMap(fn, concurrency=16)"]
        
        DemandSignal --> BufferPolicy
        BufferPolicy --> BoundedFlatMap
    end

    subgraph SlowConsumer["Slow Downstream Consumer"]
        DBWriter["Database Writer / External REST API (500 ops/sec)"]
    end

    StreamGen --> DemandSignal
    BoundedFlatMap --> DBWriter
    DBWriter -.->|Acks capacity: request next 16 items| DemandSignal
```

---

## 2. Bounding `flatMap` Concurrency

> [!CAUTION]
> **The Unbounded `flatMap` Trap**: By default, `Flux.flatMap(fn)` runs with an internal concurrency of `Queues.SMALL_BUFFER_SIZE` (256). If called on an unbounded upstream stream, it can open thousands of simultaneous database connections and socket descriptors.
> **Always specify explicit concurrency limits** on IO-bound `flatMap` operations.

```java
package com.example.service;

import com.example.model.Order;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@Slf4j
@Service
@RequiredArgsConstructor
public class BatchOrderProcessor {

    private final ExternalPaymentClient paymentClient;

    public Flux<PaymentReceipt> processOrdersSafely(Flux<Order> orderStream) {
        return orderStream
                // 🔒 Bounded Concurrency: Maximum 16 parallel downstream HTTP requests at any time!
                .flatMap(order -> paymentClient.chargeOrder(order)
                                .doOnError(ex -> log.error("Payment failed for order: {}", order.id(), ex))
                                .onErrorResume(ex -> Mono.empty()), 
                        16 // Concurrency limit
                );
    }
}
```

---

## 3. Reactor Backpressure Overflow Strategies

When a producer emits faster than a consumer can request, Reactor provides four deterministic overflow strategies:

| Strategy Operator | Behavior | Best Use Case |
| :--- | :--- | :--- |
| **`onBackpressureBuffer(maxSize, OverflowStrategy)`** | Buffers items in memory up to `maxSize`. Drops oldest/latest or errors if full. | Smoothing out momentary traffic spikes without losing events. |
| **`onBackpressureDrop(consumer)`** | Silently drops incoming items when consumer cannot keep up; invokes optional callback. | IoT sensor metrics where dropping intermittent readings is acceptable. |
| **`onBackpressureLatest()`** | Keeps only the single most recent emitted item, discarding intermediate items. | Live stock ticker UI updates where only the latest price matters. |
| **`onBackpressureError()`** | Immediately terminates the pipeline with an `Exceptions.OverflowException`. | Mission-critical financial pipelines where silent data loss is forbidden. |

### Code Implementation

```java
public Flux<SensorReading> processTelemetry(Flux<SensorReading> rawSensorStream) {
    return rawSensorStream
            // 1. Buffer up to 500 items; drop oldest if full
            .onBackpressureBuffer(
                    500,
                    dropped -> log.warn("Buffer full! Dropping oldest reading: {}", dropped.sensorId()),
                    BufferOverflowStrategy.DROP_OLDEST
            )
            // 2. Control demand batching from upstream
            .limitRate(50) // Requests 50 items at a time from publisher
            .flatMap(this::saveReadingToDatabase, 8);
}
```

---

## 4. Rate-Limiting & Sampling Operators

To slow down fast publishers before they reach downstream consumers:

```java
// 1. sample: Emits the most recent item emitted during each 500ms window
Flux<StockPrice> sampledPrices = livePriceFlux.sample(Duration.ofMillis(500));

// 2. delayElements: Enforces a minimum delay between emitted items
Flux<EmailNotification> pacedEmails = emailFlux.delayElements(Duration.ofMillis(100));

// 3. limitRate: Controls the prefetch size requested via Subscription.request(n)
Flux<Order> controlledFlux = ordersFlux.limitRate(100, 75); // Request 100, refill when 75% consumed
```

---

## 5. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Backpressure Metrics** | Micrometer observation timer on reactive pipelines. | Automatic backpressure buffer saturation and drop rate OTel metrics. |
| **Virtual Thread Interaction** | Reactive streams handle backpressure natively; Virtual Threads block carriers. | Unified non-blocking backpressure streams bridging Virtual Thread iterators. |
| **Memory Safety** | Bounded queues configured via Project Reactor defaults. | Zero-allocation ring buffers for high-speed packet processing. |

---

## 6. Primary Sources & Further Reading

- [Project Reactor: Backpressure and Reactive Streams](https://projectreactor.io/docs/core/release/reference/#reactive.backpressure).
- [Reactive Streams Specification: Demand Signals](https://github.com/reactive-streams/reactive-streams-jvm#specification).
- [Flight of the Flux: Backpressure in Action](https://spring.io/blog/2020/03/02/flight-of-the-flux-3-hopping-threads-and-schedulers).

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the primary purpose of reactive backpressure?"
    **Answer**: To allow a slow consumer to regulate the flow of data from a fast publisher via demand requests, preventing memory exhaustion and system crashes.

??? question "Question 2: What is the risk of using `Flux.flatMap(fn)` without specifying a concurrency limit?"
    **Answer**: It can spawn hundreds or thousands of simultaneous asynchronous operations, exhausting database connections and file descriptors.

??? question "Question 3: How does `onBackpressureLatest()` handle stream overflow?"
    **Answer**: It discards all intermediate unrequested items and retains only the single newest item emitted by the publisher.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0076: Real-Time Streaming with Server-Sent Events (SSE)**](0076-realtime-streaming-server-sent-events-sse.md) | [**All Lessons**](index.md) | [➡️ **0078: Integration Testing Reactive APIs with WebTestClient**](0078-integration-testing-reactive-webtestclient-testcontainers.md) |

🎉 **Lesson 0077 completed! Proceed to Lesson 0078 to master testing reactive WebFlux pipelines using `StepVerifier` and `WebTestClient`.**
