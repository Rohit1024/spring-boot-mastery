---
icon: lucide/cpu
---

# Spring Modulith and virtual threads cheatsheet

Reference guide for Modular Monolith architecture, ArchUnit module boundary verification, Spring Modulith transactional event publication, and Java 21+ virtual threads configuration.

---

## 1. Spring Modulith verification and documentation

### Architecture verification test
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

### Module package conventions
```text
com.example.app.order/            <-- Public API (Exported)
com.example.app.order.internal/   <-- Encapsulated internals (Hidden from other modules)
```

---

## 2. Transactional event publication (Outbox pattern)

### 1. Maven starter
```xml
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-jdbc</artifactId>
</dependency>
```

### 2. Publishing and consuming events
```java
// Publisher (Transactional outbox write):
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
        // Automatically marked COMPLETED in event_publication table upon return.
    }
}
```

---

## 3. Java 21+ virtual threads configuration

### 1. `application.yml`
```yaml
spring:
  threads:
    virtual:
      enabled: true
```

### 2. Thread pinning and locking rules
```java
// Synchronized blocks pin carrier threads during blocking I/O:
synchronized (lock) {
    restTemplate.getForObject(...);
}

// ReentrantLock unmounts virtual threads cleanly:
private final ReentrantLock lock = new ReentrantLock();
lock.lock();
try {
    restTemplate.getForObject(...);
} finally {
    lock.unlock();
}
```

### 3. Concurrency limiting
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

## Navigation and cheatsheet index

| Previous | Cheatsheet index | Next |
| :--- | :---: | ---: |
| [**GraphQL, gRPC, and WebSockets protocol cheatsheet**](graphql-grpc-websockets.md) | [**All cheatsheets**](index.md) | [**Prometheus, Grafana, and OpenTelemetry cheatsheet**](prometheus-grafana-opentelemetry.md) |
