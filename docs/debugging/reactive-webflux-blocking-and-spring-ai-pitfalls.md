---
icon: lucide/bug
---

# Troubleshooting Reactive WebFlux & Spring AI Pitfalls

Reactive systems and Generative AI microservices introduce specialized failure modes: silent event loop freezing, R2DBC connection pool starvation from dangling subscriptions, unbounded `flatMap` memory explosions, and LLM context window overflows.

This playbook provides root-cause analyses, diagnostic flowcharts, and concrete resolutions for common Spring WebFlux, Project Reactor, R2DBC, and Spring AI pitfalls.

---

## 1. Diagnostic Flow: WebFlux Freezes & AI Outages

``` mermaid
flowchart TD
    Issue["Symptom in WebFlux / Spring AI Stack"]

    subgraph WebFluxBranch["WebFlux & Netty Event Loop Issues"]
        ServerFreeze["Netty Worker Freezes / High Latency Spikes"]
        CheckBlockHound{"Is a blocking I/O call executing on Event Loop?"}
        FixBlockHound["Install BlockHound & offload to Schedulers.boundedElastic()"]
        CheckR2dbcPool{"Is R2DBC pool exhausted?"}
        FixR2dbcLeak["Ensure every Mono/Flux is subscribed & bounded"]
    end

    subgraph MemoryBranch["Backpressure & Heap Overflow"]
        OOMCrash["JVM Heap OOM / Exit Code 137"]
        CheckFlatMap{"Is flatMap executing unbounded concurrency?"}
        FixFlatMap["Limit flatMap concurrency: flatMap(fn, 16)"]
    end

    subgraph SpringAIBranch["Spring AI & LLM Integration"]
        LLMError["HTTP 429 Rate Limit / 400 Context Window Overflow"]
        CheckRAGChunks{"Are RAG context chunks exceeding token budget?"}
        FixRAG["Tune TokenTextSplitter chunk size and add Retry.backoff()"]
    end

    Issue --> ServerFreeze
    Issue --> OOMCrash
    Issue --> LLMError

    ServerFreeze --> CheckBlockHound
    CheckBlockHound -->|Yes| FixBlockHound
    CheckBlockHound -->|No| CheckR2dbcPool
    CheckR2dbcPool --> FixR2dbcLeak

    OOMCrash --> CheckFlatMap
    CheckFlatMap --> FixFlatMap

    LLMError --> CheckRAGChunks
    CheckRAGChunks --> FixRAG
```

---

## 2. Pitfall 1: Event Loop Thread Blocking & BlockHound Detection

### Symptom
Under a test load of just 50 requests/sec, the WebFlux service latency degrades from 5ms to over 20 seconds, and CPU utilization drops to near zero.

### Root Cause
A blocking library call (e.g. `Thread.sleep()`, JDBC call, or `FileInputStream`) is executing inside a Netty event loop thread (`reactor-http-nio-*`), freezing the thread and blocking all other concurrent requests sharing that core.

### Diagnostic & Resolution
Add **BlockHound** to detect blocking calls automatically during tests and development:

```xml
<dependency>
    <groupId>io.projectreactor.tools</groupId>
    <artifactId>blockhound</artifactId>
    <version>1.0.9.RELEASE</version>
    <scope>test</scope>
</dependency>
```

```java
// Install BlockHound in test setup or main class
@BeforeAll
static void setUpBlockHound() {
    BlockHound.install();
}
```

When a blocking call executes on an event loop, BlockHound immediately throws an actionable stack trace:
```text
reactor.blockhound.BlockingOperationError: Blocking call! java.io.FileInputStream#readBytes
    at java.io.FileInputStream.read(FileInputStream.java:279)
    at com.example.service.LegacyFileReader.readConfig(LegacyFileReader.java:14)
```

```java
// ✅ RESOLUTION: Offload blocking legacy calls to Schedulers.boundedElastic()
public Mono<String> readLegacyConfig(String path) {
    return Mono.fromCallable(() -> legacyFileReader.readConfig(path))
            .subscribeOn(Schedulers.boundedElastic());
}
```

---

## 3. Pitfall 2: R2DBC Connection Pool Starvation from Dangling Subscriptions

### Symptom Log
```text
io.r2dbc.pool.ConnectionPoolTimeoutException: 
Timeout acquiring connection for 30000ms [pool-size: 30, active: 30, pending: 450]
```

### Root Cause
1. **Unsubscribed Assembly**: Assembling an R2DBC query without returning the `Mono`/`Flux` in the controller response chain. In Reactor, if a pipeline is subscribed to partially and abandoned without a `cancel` signal, the underlying R2DBC connection remains reserved.
2. **Missing Timeout**: Queries on deadlocked tables hold connections indefinitely.

### Resolution
Always chain timeout operators and verify reactive pipeline consumption:

```java
// ✅ RESOLUTION: Enforce timeouts and guarantee disposal
public Mono<Product> getProductWithGuard(Long id) {
    return productR2dbcRepository.findById(id)
            .timeout(Duration.ofSeconds(3)) // Release connection if DB fails to respond in 3s
            .doOnError(TimeoutException.class, ex -> log.error("Database query timed out for ID: {}", id));
}
```

---

## 4. Pitfall 3: Unbounded `flatMap` Memory Explosion

### Symptom
When processing a bulk import of 50,000 items, the microservice crashes with `java.lang.OutOfMemoryError: Java heap space` or Kubernetes `OOMKilled` (Exit Code 137).

### Root Cause
Calling `Flux.fromIterable(hugeList).flatMap(service::call)` triggers all 50,000 asynchronous calls concurrently, creating 50,000 in-flight HTTP request buffers and socket handlers.

### Resolution
Enforce explicit concurrency limits on `flatMap`:

```java
// ❌ DANGEROUS: Spawns unbounded concurrent network calls
// itemsFlux.flatMap(item -> paymentClient.charge(item));

// ✅ RESOLUTION: Bounded Concurrency (Max 16 concurrent requests)
public Flux<Receipt> processBulkItems(Flux<Item> itemsFlux) {
    return itemsFlux
            .flatMap(paymentClient::charge, 16); // Bounded to 16 concurrent executions
}
```

---

## 5. Pitfall 4: Spring AI Rate Limits & Token Window Overflow

### Symptom Log
```text
org.springframework.ai.retry.NonTransientAiException: 
429 Too Many Requests: Rate limit reached for model gpt-4o in organization org-123
```

### Root Cause
High-concurrency user requests overwhelm the LLM API quota (Requests Per Minute / Tokens Per Minute). Additionally, injecting large un-chunked RAG documents exceeds the maximum context window token limit (e.g. 128k tokens).

### Resolution
1. Configure Spring AI exponential retry policies in `application.yml`:

```yaml
spring:
  ai:
    retry:
      max-attempts: 5
      backoff:
        initial-interval: 2000ms
        multiplier: 2.0
        max-interval: 10000ms
```

2. Budget RAG context chunks with `TokenTextSplitter`:

```java
// ✅ RESOLUTION: Safe chunk budgeting (800 tokens max per chunk, Top-K = 3)
TokenTextSplitter splitter = new TokenTextSplitter(800, 100, 5, 5000, true);
```

---

## 🧭 Navigation & Diagnostic Playbooks

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Troubleshooting Microservices & SAGA**](microservices-circuit-breaker-and-distributed-transaction-pitfalls.md) | [**All Debugging Guides**](index.md) | 🏆 **All Diagnostic Playbooks Completed!** |
