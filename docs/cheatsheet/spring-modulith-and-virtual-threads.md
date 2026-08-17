---
icon: lucide/cpu
---

# Spring Modulith & Virtual Threads Cheatsheet

A rapid reference guide for Modular Monolith architecture, ArchUnit module boundary verification, Spring Modulith Transactional Event Publication, and Java 21+ Virtual Threads (Project Loom) configuration.

---

## 1. Spring Modulith Verification & Documentation

### Architecture Verification Test:
```java
@Test
void verifyModularStructure() {
    ApplicationModules modules = ApplicationModules.of(Application.class);
    // Verifies zero illegal package-private cross-module dependencies:
    modules.verify();
    
    // Auto-generates living architecture diagrams:
    new Documenter(modules)
            .writeDocumentation()
            .writeModulesAsPlantUml();
}
```

### Module Package Conventions:
```text
com.example.app.order/            <-- Public API (Exported)
com.example.app.order.internal/   <-- Encapsulated Internals (Hidden from other modules)
```

---

## 2. Transactional Event Publication (Outbox Pattern)

### 1. Maven Starter:
```xml
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-jdbc</artifactId>
</dependency>
```

### 2. Publishing & Consuming Events:
```java
// Publisher (Transactional Outbox write):
@Transactional
public void placeOrder() {
    orderRepository.save(order);
    eventPublisher.publishEvent(new OrderPlacedEvent(order.getId()));
}

// Consumer (Asynchronous AFTER_COMMIT execution):
@Component
public class PaymentListener {
    @ApplicationModuleListener
    public void onOrderPlaced(OrderPlacedEvent event) {
        // Automatically marked COMPLETED in event_publication table upon return!
    }
}
```

---

## 3. Java 21+ Virtual Threads Configuration

### 1. `application.yml`:
```yaml
spring:
  threads:
    virtual:
      enabled: true
```

### 2. Best Practices & Locking:
```java
// ❌ WRONG: synchronized blocks pin carrier threads during blocking I/O!
synchronized (lock) {
    restTemplate.getForObject(...);
}

// ✅ CORRECT: ReentrantLock unmounts Virtual Threads cleanly!
private final ReentrantLock lock = new ReentrantLock();
lock.lock();
try {
    restTemplate.getForObject(...);
} finally {
    lock.unlock();
}
```

### 3. Concurrency Limiting:
```java
// Limit downstream calls to max 20 concurrent requests without thread pools:
private final Semaphore semaphore = new Semaphore(20);

public void callDownstream() throws InterruptedException {
    semaphore.acquire();
    try {
        externalClient.call();
    } finally {
        semaphore.release();
    }
}
```

---

## 🧭 Navigation & Cheatsheet Index

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **GraphQL, gRPC & WebSockets Cheatsheet**](graphql-grpc-websockets.md) | [**All Cheatsheets**](index.md) | [➡️ **Prometheus, Grafana & OTel Cheatsheet**](prometheus-grafana-opentelemetry.md) |
