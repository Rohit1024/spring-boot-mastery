---
icon: lucide/mail-check
---

# 0065: Guaranteed Message Delivery: Transactional Outbox Pattern with PostgreSQL & Kafka

When developing distributed event-driven microservices, developers frequently encounter the fatal **Dual-Write Problem**:

```java
@Transactional
public void placeOrder(OrderRequest req) {
    orderRepository.save(new Order(req)); // 1. Write to PostgreSQL
    kafkaTemplate.send("orders", event);   // 2. Write to Apache Kafka
}
```

If the Kafka cluster experiences a network timeout, the database transaction rolls back, but an event might already be in-flight. Conversely, if the database commits but the application crashes before `kafkaTemplate.send()` finishes, the event is permanently lost, causing data inconsistency across microservices.

The **Transactional Outbox Pattern** guarantees **at-least-once message delivery** by atomically saving both the domain entity and an outbox event in the same local database transaction.

In this lesson, you will master the dual-write dilemma, implement an Outbox entity table in PostgreSQL, configure a concurrent Polling Publisher using `SKIP LOCKED`, and explore Debezium Change Data Capture (CDC).

---

## 1. Transactional Outbox Architecture

``` mermaid
flowchart TD
    subgraph ClientReq["Client Request"]
        OrderCall["POST /api/v1/orders"]
    end

    subgraph ServiceLayer["Order Microservice (Spring Boot)"]
        OrderSvc["OrderService (@Transactional)"]
        PollingRelay["OutboxPublisher (Scheduled Worker / Debezium CDC)"]
    end

    subgraph PostgreSQLDB["PostgreSQL Database (ACID Boundary)"]
        OrdersTable["Table: 'orders'"]
        OutboxTable["Table: 'outbox_events' (Status: PENDING)"]
        
        OrdersTable ~~~ OutboxTable
    end

    subgraph KafkaCluster["Apache Kafka Cluster"]
        KafkaTopic["Topic: 'order-events'"]
    end

    OrderCall --> OrderSvc
    OrderSvc -->|1. Atomic INSERT in single SQL transaction| OrdersTable
    OrderSvc -->|1. Atomic INSERT in single SQL transaction| OutboxTable

    OutboxTable -.->|2. Read unprocessed rows with SKIP LOCKED| PollingRelay
    PollingRelay -->|3. Publish Event with acks=all| KafkaTopic
    KafkaTopic -.->|4. Update status to PROCESSED / Delete row| OutboxTable
```

---

## 2. The PostgreSQL Outbox Schema

Create the dedicated `outbox_events` table:

```sql
CREATE TABLE outbox_events (
    id UUID PRIMARY KEY,
    aggregate_type VARCHAR(64) NOT NULL,
    aggregate_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_outbox_pending ON outbox_events(status, created_at) WHERE status = 'PENDING';
```

---

## 3. Atomic Entity & Outbox Persistence

```java
package com.example.service;

import com.example.model.Order;
import com.example.model.OutboxEvent;
import com.example.repository.OrderRepository;
import com.example.repository.OutboxRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class OrderApplicationService {

    private final OrderRepository orderRepository;
    private final OutboxRepository outboxRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    public Order createOrder(String customerId, double amount) {
        // 1. Persist domain aggregate
        Order order = new Order(customerId, amount);
        Order savedOrder = orderRepository.save(order);

        // 2. Persist outbox event atomically in the exact same database transaction
        try {
            String payloadJson = objectMapper.writeValueAsString(savedOrder);
            OutboxEvent outboxEvent = OutboxEvent.builder()
                    .id(UUID.randomUUID())
                    .aggregateType("ORDER")
                    .aggregateId(savedOrder.getId().toString())
                    .eventType("ORDER_CREATED")
                    .payload(payloadJson)
                    .status("PENDING")
                    .createdAt(Instant.now())
                    .build();

            outboxRepository.save(outboxEvent);
            log.info("Order {} and Outbox event saved atomically", savedOrder.getId());
        } catch (Exception e) {
            throw new RuntimeException("Failed to serialize outbox event", e);
        }

        return savedOrder;
    }
}
```

---

## 4. Concurrent Polling Publisher with `SKIP LOCKED`

When running multiple instances of `order-service`, workers must not pick up the same outbox rows. PostgreSQL `FOR UPDATE SKIP LOCKED` allows workers to lock different batches concurrently without blocking each other:

```java
package com.example.repository;

import com.example.model.OutboxEvent;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.UUID;

@Repository
public interface OutboxRepository extends JpaRepository<OutboxEvent, UUID> {

    @Query(value = """
        SELECT * FROM outbox_events 
        WHERE status = 'PENDING' 
        ORDER BY created_at ASC 
        LIMIT 50 
        FOR UPDATE SKIP LOCKED
        """, nativeQuery = true)
    List<OutboxEvent> fetchPendingEventsForProcessing();
}
```

### The Scheduled Outbox Relay Worker

```java
package com.example.worker;

import com.example.model.OutboxEvent;
import com.example.repository.OutboxRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.Instant;
import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
public class OutboxMessageRelayWorker {

    private final OutboxRepository outboxRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;

    @Scheduled(fixedDelay = 500) // Poll every 500ms
    @Transactional
    public void publishPendingEvents() {
        List<OutboxEvent> events = outboxRepository.fetchPendingEventsForProcessing();
        if (events.isEmpty()) {
            return;
        }

        for (OutboxEvent event : events) {
            try {
                // Key ensures partition ordering for this aggregate
                kafkaTemplate.send("order-events", event.getAggregateId(), event.getPayload()).get();
                
                // Mark processed or delete to prevent table bloat
                event.setStatus("PROCESSED");
                event.setProcessedAt(Instant.now());
                log.info("Outbox event {} published to Kafka successfully", event.getId());
            } catch (Exception e) {
                log.error("Failed to relay outbox event {}", event.getId(), e);
                break; // Stop batch on Kafka failure to preserve sequential ordering
            }
        }
    }
}
```

---

## 5. Polling Publisher vs Debezium CDC

| Dimension | Scheduled Polling Publisher | Debezium Change Data Capture (CDC) |
| :--- | :--- | :--- |
| **Mechanism** | Application polls SQL table via `SELECT ... SKIP LOCKED`. | Kafka Connect engine tails PostgreSQL Write-Ahead Log (WAL). |
| **Latency** | Polling interval dependent (100–500ms). | Near real-time (< 10ms). |
| **Database Overhead** | Regular SQL query CPU and index lookups. | Minimal zero-query WAL streaming overhead. |
| **Operational Stack** | Pure Java / Spring Boot application code. | Requires Kafka Connect cluster and Debezium connector plugins. |

---

## 6. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Transactional Events** | Spring Modulith `@ApplicationModuleListener` with built-in JPA event publication registry. | Native kernel outbox streaming with zero manual scheduled worker setup. |
| **PostgreSQL Integration** | PostgreSQL 16 `JSONB` column mapping via Hibernate 6.x. | Zero-allocation binary event serialization with PostgreSQL logical replication streams. |
| **Cloud-Native CDC** | Debezium Kafka Connect connector. | Native Spring Boot direct Postgres WAL replication stream client. |

---

## 7. Primary Sources & Further Reading

- [Microservices Patterns: Transactional Outbox — Chris Richardson](https://microservices.io/patterns/data/transactional-outbox.html).
- [Debezium Official Documentation](https://debezium.io/documentation/reference/stable/architecture.html) — Outbox event routing and WAL streaming.
- [Spring Modulith Transactional Event Publication](https://docs.spring.io/spring-modulith/reference/events.html#publication-registry).

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the Dual-Write problem in microservices?"
    **Answer**: The risk of data inconsistency when an application attempts to write to both a database and a message broker without distributed transaction guarantees.

??? question "Question 2: How does PostgreSQL `FOR UPDATE SKIP LOCKED` prevent race conditions in polling workers?"
    **Answer**: It locks rows selected by one worker and causes other concurrent workers to skip already-locked rows without waiting, enabling safe parallel polling.

??? question "Question 3: Why does the Transactional Outbox Pattern guarantee at-least-once rather than exactly-once delivery?"
    **Answer**: Because the worker might successfully publish to Kafka but crash before updating the outbox table status to PROCESSED, causing a redelivery upon restart.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0064: Distributed Transactions: SAGA Pattern**](0064-distributed-transactions-saga-pattern.md) | [**All Lessons**](index.md) | [➡️ **0066: High-Scale Reads: CQRS Architecture**](0066-high-scale-reads-cqrs-architecture.md) |

🎉 **Lesson 0065 completed! Proceed to Lesson 0066 to master read/write segregation with the CQRS pattern.**
