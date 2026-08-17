---
icon: lucide/bug
---

# Troubleshooting Spring Modulith & Virtual Thread Pinning Pitfalls

Modular Monoliths and Java 21+ Virtual Threads offer massive architectural and throughput advantages, but introduce new failure modes. Module boundary violations break architectural integrity, uncompleted outbox events stall workflows, and carrier thread pinning silently eliminates Virtual Thread scalability.

This playbook provides root-cause diagnostic workflows, reproducible scenarios, and production-tested solutions for Spring Modulith and Project Loom concurrency issues.

---

## 1. Diagnostic Decision Tree

``` mermaid
flowchart TD
    Start["Modulith or Virtual Thread Issue Detected"] --> ErrType{"Identify Failure Category"}

    ErrType -->|Architecture Test Failure| ArchErr["1. Cross-Module Package Violation"]
    ErrType -->|Outbox Rows Stuck in Database| OutboxErr["2. Incomplete Event Publications"]
    ErrType -->|Carrier Thread Starvation| PinningErr["3. Virtual Thread Carrier Pinning"]

    ArchErr --> FixArch["Export public API DTO or move package-private internals"]
    OutboxErr --> FixOutbox["Add @ApplicationModuleListener & configure IncompleteEventPublications"]
    PinningErr --> FixPinning["Run -Djdk.tracePinnedThreads=full & replace synchronized with ReentrantLock"]
```

---

## 2. Issue 1: Modulith Package Encapsulation Violation

### Symptoms & Error Log
Running unit tests triggers `org.springframework.modulith.core.Violations`:

```text
org.springframework.modulith.core.Violations: 
- Module 'inventory' depends on non-exposed type 'com.example.ecommerce.order.internal.OrderRepository' via parameter 'orderRepository' in 'com.example.ecommerce.inventory.internal.StockService(OrderRepository)'!
- Cyclical dependency detected between modules 'order' and 'payment'!
```

### Root Cause
1. A bean in `inventory` directly imports an internal, non-exported class from the `order.internal` package.
2. Direct bean cross-injection creates a circular dependency between module bounded contexts.

### Resolution
1. Expose a public API interface/service at the root of the `order` package (e.g. `com.example.ecommerce.order.OrderPublicApi`).
2. Decouple inter-module circular calls using **Domain Events** (`OrderPlacedEvent`) and `@ApplicationModuleListener` instead of direct bean injection.

---

## 3. Issue 2: Virtual Thread Carrier Pinning

### Symptoms & Error Log
Under moderate load (e.g. 500 concurrent requests), response latency spikes from 20ms to 8,000ms, CPU utilization drops, and Tomcat stops accepting new connections even with `spring.threads.virtual.enabled=true`.

### Root Cause
A blocking I/O operation (JDBC query, `RestTemplate`, or `Thread.sleep()`) is executed inside a Java `synchronized (lock)` block or method, pinning the underlying OS carrier thread in the `ForkJoinPool`.

### Diagnostic Flowchart

``` mermaid
sequenceDiagram
    autonumber
    actor Client as HTTP Traffic
    participant VT as Virtual Thread
    participant Carrier as OS Carrier Thread (ForkJoinPool)
    participant Lock as synchronized (monitor)

    Client->>VT: 500 Concurrent Requests
    VT->>Lock: Enters synchronized(this) { ... }
    VT->>VT: Calls restTemplate.getForObject(...) [Blocks on I/O]
    Note over VT,Carrier: 💥 PINNED! JVM cannot unmount VT from Carrier!
    Carrier--xCarrier: Carrier thread is frozen and cannot process other VTs!
```

### Enabling Pinning Stack Traces
Start the JVM with diagnostic logging:
```bash
java -Djdk.tracePinnedThreads=full -jar application.jar
```

Stack trace output:
```text
Thread[#42,ForkJoinPool-worker-1,5,CarrierThreads]
    java.base/java.lang.VirtualThread$VThreadContinuation.onPinned(VirtualThread.java:185)
    com.example.service.LegacyPaymentGateway.execute(LegacyPaymentGateway.java:24) <== synchronized
```

### Resolution
Refactor `synchronized` blocks to `ReentrantLock`:

```java
// ❌ PINNING ANTI-PATTERN
public synchronized String callExternalService() {
    return restTemplate.getForObject(url, String.class);
}

// ✅ CLEAN LOOM CODE
private final ReentrantLock lock = new ReentrantLock();

public String callExternalService() {
    lock.lock();
    try {
        return restTemplate.getForObject(url, String.class);
    } finally {
        lock.unlock();
    }
}
```

---

## 🧭 Navigation & Diagnostic Playbooks

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Troubleshooting GraphQL, gRPC & WebSockets**](graphql-n-plus-1-grpc-and-websocket-broker-pitfalls.md) | [**All Debugging Guides**](index.md) | [➡️ **Prometheus & OpenTelemetry Debugging**](prometheus-scraping-and-opentelemetry-collector-pitfalls.md) |
