---
icon: lucide/zap
---

# 0044: Concurrency: Java 21 virtual threads (Project Loom) in Spring Boot

For decades, Java applications scaled concurrent web requests using **OS-bound Platform Threads** (1:1 mapped to operating system kernel threads). Because each platform thread consumes ~1MB of memory and requires expensive kernel context switching, embedded servers like Tomcat capped worker thread pools at **200 threads**. When all 200 threads blocked on database queries or external REST calls, the server stalled and dropped incoming traffic.

While Reactive Programming (Spring WebFlux) solved thread scalability by using non-blocking event loops, it introduced immense programming complexity: reactive pipelines (`Mono`/`Flux`), fragmented stack traces, and incompatible blocking libraries (JPA/JDBC).

**Java 21+ Virtual Threads (Project Loom)** deliver the ultimate concurrency breakthrough: **writing clean, synchronous, blocking Java code that achieves reactive-level throughput** with millions of lightweight threads.

In this lesson, you will master Virtual Thread internals, configure Spring Boot 3.2+ / 4.x with `spring.threads.virtual.enabled=true`, diagnose **Thread Pinning**, and avoid `ThreadLocal` memory traps.

---

## 1. Platform threads vs WebFlux vs virtual threads

``` mermaid
flowchart TD
    subgraph PlatformThreads["1. OS Platform Threads (1:1 Model)"]
        Req1["Request 1"] --> PT1["Platform Thread 1 (~1MB RAM)"]
        Req2["Request 2"] --> PT2["Platform Thread 2 (~1MB RAM)"]
        PT1 & PT2 -->|Blocks on JDBC or REST Call| OSKernel["OS Kernel Context Switch (High CPU Overhead)"]
        PTLimit["❌ Hard ceiling of ~200-500 threads per JVM"]
        OSKernel --- PTLimit
    end

    subgraph VirtualThreads["2. Java 21+ Virtual Threads (M:N Loom Model)"]
        VReq1["Request 1"] --> VT1["Virtual Thread 1 (~1KB RAM)"]
        VReq2["Request 2"] --> VT2["Virtual Thread 2 (~1KB RAM)"]
        VReq3["Request 3"] --> VT3["Virtual Thread 3 (~1KB RAM)"]
        
        VT1 & VT2 & VT3 -->|Mounted & Scheduled| CarrierPool["ForkJoinPool Carrier Threads (Equal to CPU Cores)"]
        CarrierPool --> OSKernel2["Zero OS Kernel Context Switching"]
        VTScale["✅ Millions of concurrent virtual threads"]
        OSKernel2 --- VTScale
    end

    PlatformThreads ~~~ VirtualThreads
```

---

## 2. Enabling virtual threads in Spring Boot

In Spring Boot 3.2+ and 4.x, enabling Virtual Threads across Tomcat, `@Async` tasks, `@Scheduled` jobs, and messaging listeners requires a single configuration property:

### `application.yml`
```yaml
spring:
  threads:
    virtual:
      enabled: true
```

### What happens under the hood?
1. **Embedded Tomcat**: Switches its request execution engine from a fixed `ThreadPoolExecutor` (default 200 platform threads) to `Executors.newVirtualThreadPerTaskExecutor()`. Every HTTP request runs on its own dedicated Virtual Thread!
2. **Spring `@Async`**: Automatically uses virtual threads for asynchronous methods without custom executor bean boilerplate.
3. **Spring MVC Controllers**: Standard blocking JDBC / JPA repository calls, `RestTemplate`, or `Thread.sleep()` unmount smoothly from the underlying carrier thread without consuming OS resources.

---

## 3. The unmounting lifecycle during blocking i/o

``` mermaid
sequenceDiagram
    autonumber
    actor Client as HTTP Client
    participant VT as Virtual Thread (Tomcat Request)
    participant Carrier as OS Carrier Thread (ForkJoinPool-worker-1)
    participant DB as PostgreSQL Database

    Client->>VT: Incoming HTTP Request
    VT->>Carrier: Mount Virtual Thread onto Carrier
    Carrier->>DB: Execute Blocking JDBC Query (e.g. findById)
    Note over VT,Carrier: ⚡ I/O Blocking detected! JVM captures Continuation stack frame!
    VT-->>Carrier: Unmounts VT from Carrier (Carrier is now FREE to run other requests!)
    DB-->>Carrier: Query Result Returned after 100ms
    Carrier->>VT: Remounts VT (on ANY available carrier thread) & Resumes Execution
    VT-->>Client: 200 OK Response
```

---

## 4. The critical pitfall: Thread pinning (`synchronized` blocks)

### What is carrier thread pinning?
A Virtual Thread is **pinned** to its OS carrier thread if it attempts a blocking I/O operation inside:
1. A `synchronized` method or `synchronized (lock)` block.
2. A native method / Java Native Interface (JNI) call.

When pinned, the Virtual Thread **cannot unmount**. The carrier thread remains frozen and blocked, starving the entire `ForkJoinPool` carrier pool!

``` mermaid
flowchart TD
    subgraph BadCode["❌ Pinning Code (synchronized block)"]
        SyncMethod["synchronized void doCriticalWork() {<br/>&nbsp;&nbsp;&nbsp;&nbsp;restTemplate.getForObject(...); // 💥 BLOCKS & PINS CARRIER THREAD!<br/>}"]
    end

    subgraph GoodCode["✅ Clean Loom Code (ReentrantLock)"]
        LockMethod["private final ReentrantLock lock = new ReentrantLock();<br/>void doCriticalWork() {<br/>&nbsp;&nbsp;&nbsp;&nbsp;lock.lock();<br/>&nbsp;&nbsp;&nbsp;&nbsp;try { restTemplate.getForObject(...); } // ✅ Unmounts cleanly!<br/>&nbsp;&nbsp;&nbsp;&nbsp;finally { lock.unlock(); }<br/>}"]
    end

    BadCode ~~~ GoodCode
```

### Detecting pinning at runtime
Pass the JVM diagnostic flag on application startup to detect pinned threads:
```bash
java -Djdk.tracePinnedThreads=full -jar app.jar
```

---

## 5. Golden rules for virtual threads

| Practice | Recommendation | Rationale |
| :--- | :--- | :--- |
| **Thread Pooling** | ❌ **NEVER Pool Virtual Threads** (`newFixedThreadPool`). | Virtual threads are cheap and ephemeral (~1KB); creating a new one per task is faster than pool management. |
| **Concurrency Limiting** | ✅ Use `Semaphore` instead of thread pools. | To limit concurrent calls to a database or rate-limited third-party API, use a `Semaphore(50)`. |
| **`ThreadLocal` Usage** | ⚠️ Avoid caching large data objects in `ThreadLocal`. | In an application with 500,000 active virtual threads, large `ThreadLocal` allocations cause severe heap exhaustion. |

---

## 6. Spring Boot 3 vs Spring Boot 4: Concurrency evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Java 21)"]
        TomcatVirtual["Tomcat VirtualThreadPerTaskExecutor"]
        ScopedValuesPreview["JEP 429 Scoped Values (Preview)"]
        ManualLocks["Refactoring synchronized to ReentrantLock"]
    end

    subgraph SB4["Spring Boot 4.x (Java 25+)"]
        FullLoomStandard["Loom-First Standard Container Architecture"]
        ScopedValuesStandard["Native ScopedValue Context Propagation (Replaces ThreadLocal)"]
        JvmUnpinning["JVM Auto-Unpinning of synchronized Blocks"]
    end

    SB3 ==>|Full Framework Virtual Thread Modernization| SB4
```

### Key differences and configuration comparison

| Concurrency Dimension | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Virtual Thread Property** | `spring.threads.virtual.enabled=true` (Opt-in feature). | **Virtual Threads Enabled by Default** on supported JDK 25+ runtimes. |
| **Context Propagation** | Relied on `ThreadLocal` inheritance with MDC / Security context copying. | **Java Scoped Values (`ScopedValue`)**: High-performance, immutable, bounded context propagation. |
| **Synchronization Pinning** | `synchronized` blocks pinned carrier threads. | **JVM JEP 491 Unpinning**: Synchronized monitors unmount automatically on modern JDKs. |

---

## 7. Primary sources and further reading

- [JEP 444: Virtual Threads (Java 21 Official Specification)](https://openjdk.org/jeps/444), Core design, carrier scheduler, and continuations.
- [Spring Boot Virtual Threads Official Documentation](https://docs.spring.io/spring-boot/reference/features/spring-application.html#features.spring-application.virtual-threads), Auto-configuration behavior.
- [Inside Java: Embracing Virtual Threads in Spring Boot](https://inside.java/tag/loom/), Best practices and performance benchmarks.

---

## 8. Knowledge check and practice

??? question "Question 1: Why is it an anti-pattern to create a thread pool for Virtual Threads (e.g. `Executors.newFixedThreadPool(100)`)?"
    **Answer**: Virtual threads are lightweight (~1KB) and designed to be ephemeral (created per-task and discarded immediately); pooling them adds unnecessary synchronization overhead.

??? question "Question 2: What causes a Virtual Thread to "pin" its underlying OS carrier thread?"
    **Answer**: Executing a blocking I/O operation inside a `synchronized` block or invoking native JNI methods prevents the JVM from unmounting the virtual thread.

??? question "Question 3: How does Spring Boot handle blocking database queries differently when `spring.threads.virtual.enabled=true` is set?"
    **Answer**: The Virtual Thread running the request unmounts from its carrier thread during the blocking JDBC call, allowing the carrier thread to serve other requests until the database responds.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0043: Transactional Event Publication**](0043-transactional-event-publication-spring-modulith.md) | [**All Lessons**](index.md) | [ **0045: Production Metrics with Prometheus**](0045-production-metrics-prometheus-scraping-promql.md) |

**Module 9 completed.**
