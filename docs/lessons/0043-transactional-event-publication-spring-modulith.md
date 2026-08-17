---
icon: lucide/mail-check
---

# 0043: Decoupling Modules with Transactional Event Publication

When building modular monoliths, coupling modules together through direct synchronous service injection (e.g. `OrderService` calling `PaymentService` and `EmailNotificationService`) violates Domain-Driven Design (DDD) boundaries and bundles unrelated operations into a single fragile database transaction.

Standard Spring `@EventListener` promises asynchronous event decoupling, but introduces a fatal **dual-write failure risk**: if the JVM crashes right after committing the database transaction, in-memory events are permanently lost.

Spring Modulith solves this with the **Transactional Event Publication Registry**—an outbox pattern built directly into your modular monolith that guarantees **at-least-once transactional event delivery**.

In this lesson, you will master publishing domain events, consuming them with `@ApplicationModuleListener`, and managing persistent event outbox tables.

---

## 1. Synchronous Coupling vs Transactional Events

``` mermaid
flowchart TD
    subgraph DirectCoupling["❌ Synchronous Service Coupling (Brittle Transaction)"]
        TxStart["1. Begin Transaction: OrderService.createOrder()"]
        CallPay["2. Direct Call: PaymentService.charge()"]
        CallMail["3. Direct Call: EmailService.sendEmail() [Fails / Times Out!]"]
        RollbackAll["💥 Whole Order Rolls Back due to Email Timeout!"]
        
        TxStart --> CallPay --> CallMail --> RollbackAll
    end

    subgraph ModulithOutbox["✅ Spring Modulith Transactional Event Publication"]
        OrderTx["1. Order DB Insert + Event Publication (Atomic Transaction)"]
        EventTable[("event_publication Outbox Table<br/><i>(Stores OrderPlacedEvent)</i>")]
        Listener["2. @ApplicationModuleListener (Asynchronous AFTER_COMMIT)"]
        MarkComplete["3. Mark Event COMPLETED in event_publication"]
        
        OrderTx -->|Atomic Commit| EventTable
        EventTable -->|Triggers Decoupled Listener| Listener --> MarkComplete
    end

    DirectCoupling ~~~ ModulithOutbox
```

---

## 2. Setting Up the Event Publication Registry

Spring Modulith provides auto-configured starter modules for relational databases:

### Maven Dependency (`pom.xml`)
```xml
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-jdbc</artifactId>
</dependency>
```

### Automatic Table Initialization (`event_publication`)
Spring Modulith creates the outbox table automatically:

```sql
CREATE TABLE event_publication (
    id UUID NOT NULL PRIMARY KEY,
    event_type VARCHAR(512) NOT NULL,
    listener_id VARCHAR(512) NOT NULL,
    serialized_event TEXT NOT NULL,
    publication_date TIMESTAMP WITH TIME ZONE NOT NULL,
    completion_date TIMESTAMP WITH TIME ZONE
);
```

---

## 3. Publishing Domain Events from an Application Module

Domain events are immutable Java Records representing facts that have occurred in the domain:

### `OrderPlacedEvent.java` (Domain Event)
```java
package com.example.ecommerce.order;

import java.math.BigDecimal;

public record OrderPlacedEvent(
        Long orderId,
        Long customerId,
        BigDecimal totalAmount
) {}
```

### `OrderService.java` (Publishing Event)
```java
package com.example.ecommerce.order;

import com.example.ecommerce.order.internal.OrderEntity;
import com.example.ecommerce.order.internal.OrderRepository;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderService {

    private final OrderRepository orderRepository;
    private final ApplicationEventPublisher eventPublisher;

    public OrderService(OrderRepository orderRepository, ApplicationEventPublisher eventPublisher) {
        this.orderRepository = orderRepository;
        this.eventPublisher = eventPublisher;
    }

    @Transactional
    public Long createOrder(Long customerId, java.math.BigDecimal amount) {
        // 1. Save business entity in database
        OrderEntity entity = new OrderEntity(customerId, amount);
        orderRepository.save(entity);

        // 2. Publish Domain Event (Atomically written to 'event_publication' in this TX!)
        eventPublisher.publishEvent(new OrderPlacedEvent(entity.getId(), customerId, amount));

        return entity.getId();
    }
}
```

---

## 4. Consuming Events with `@ApplicationModuleListener`

The `@ApplicationModuleListener` annotation simplifies asynchronous event handling by automatically combining:
- `@Async` (Executes in a separate thread pool or Virtual Thread).
- `@Transactional(propagation = Propagation.REQUIRES_NEW)` (Dedicated transaction for the listener).
- `@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)` (Only fires if the publishing transaction committed successfully).

### `PaymentModuleListener.java` (In `payment` module)
```java
package com.example.ecommerce.payment;

import com.example.ecommerce.order.OrderPlacedEvent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.modulith.events.ApplicationModuleListener;
import org.springframework.stereotype.Component;

@Component
public class PaymentModuleListener {

    private static final Logger log = LoggerFactory.getLogger(PaymentModuleListener.class);

    @ApplicationModuleListener
    public void onOrderPlaced(OrderPlacedEvent event) {
        log.info("Payment Module received OrderPlacedEvent for Order ID: {}", event.orderId());
        
        // Execute payment processing...
        // Upon successful method exit, Spring Modulith marks the event publication as COMPLETED!
    }
}
```

---

## 5. Incomplete Event Resubmission & Crash Recovery

If a consuming listener throws an unhandled exception or the server crashes midway, the event remains in `event_publication` with `completion_date = NULL`.

You can automatically resubmit uncompleted events on startup or via a scheduled job:

```java
package com.example.ecommerce.config;

import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.modulith.events.IncompleteEventPublications;

import java.time.Duration;

@Configuration
public class EventResubmissionConfig {

    @Bean
    public ApplicationRunner resubmitFailedEvents(IncompleteEventPublications publications) {
        return args -> {
            // Resubmit any publications that failed or were abandoned for more than 5 minutes
            publications.resubmitIncompletePublicationsOlderThan(Duration.ofMinutes(5));
        };
    }
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4: Event Registry Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Spring Modulith 1.1+)"]
        JdbcRegistry["JDBC / JPA Event Publication Registry"]
        PlatformAsync["ThreadPoolTaskExecutor Event Dispatch"]
        ManualCronReplay["Manual @Scheduled Resubmission Beans"]
    end

    subgraph SB4["Spring Boot 4.x (Spring Modulith 2.0)"]
        ZeroSerialization["Native JSONB / Protobuf Binary Outbox Format"]
        VirtualThreadEvents["Virtual-Thread Native Event Listeners"]
        AutoReplayEngine["Built-in Autonomous Dead-Letter Auto-Replay Engine"]
    end

    SB3 ==>|Loom Concurrency & High-Speed Outbox| SB4
```

### Key Differences & Configuration Comparison

| Event Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Listener Threading** | Platform thread pool (`@Async` with `ThreadPoolTaskExecutor`). | **Virtual Thread Dispatching**: Every event listener spawns an isolated virtual thread without pool saturation. |
| **Event Serialization** | Jackson JSON string column (`serialized_event TEXT`). | **Native Postgres JSONB & Protobuf**: Binary zero-copy event persistence for 5x faster throughput. |
| **Outbox Purge Engine** | Required manual scheduled tasks to delete completed publications. | **Auto-Archiving & Partitioning**: Automatic partition rotation for `event_publication` tables. |

---

## 7. Primary Sources & Further Reading

- [Spring Modulith: Working with Events Reference](https://docs.spring.io/spring-modulith/reference/events.html) — Event publication registry, listener semantics, and transactional guarantees.
- [Transactional Outbox Pattern by Chris Richardson](https://microservices.io/patterns/data/transactional-outbox.html) — Core theory and architecture.
- [Baeldung: Spring Modulith Deep Dive](https://www.baeldung.com/spring-modulith) — Practical guides on events and module testing.

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What catastrophic failure occurs when using standard Spring `@Async` `@EventListener` without an outbox registry?"
    **Answer**: If the server crashes after the database transaction commits but before the asynchronous in-memory event listener executes, the event is permanently lost with no record in the database.

??? question "Question 2: What three annotations are encapsulated by Spring Modulith's `@ApplicationModuleListener`?"
    **Answer**: `@Async`, `@Transactional(propagation = REQUIRES_NEW)`, and `@TransactionalEventListener(phase = AFTER_COMMIT)`.

??? question "Question 3: How does the `event_publication` table guarantee at-least-once event delivery across application restarts?"
    **Answer**: Events are saved atomically in the same database transaction as business entities; if a listener fails, the row remains with `completion_date = NULL` and can be automatically replayed.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0042: Spring Modulith Modular Monoliths**](0042-spring-modulith-modular-monoliths-ddd.md) | [**All Lessons**](index.md) | [➡️ **0044: Java 21 Virtual Threads (Loom)**](0044-java-virtual-threads-project-loom-spring-boot.md) |
