---
icon: lucide/split
---

# 0066: High-scale reads: CQRS architecture

In standard CRUD architectures, a single domain model and database schema handle both write mutations (`INSERT`, `UPDATE`) and read queries (`SELECT`). As traffic scales to millions of users, this unified model breaks down:
- **Write Operations** require strict third-normal-form (3NF) relational models, foreign key constraints, and pessimistic/optimistic locks to enforce business invariants.
- **Read Operations** require denormalized, flattened data graphs, complex multi-table aggregations, and sub-millisecond full-text search queries.

**CQRS (Command Query Responsibility Segregation)** completely separates the Write (Command) model from the Read (Query) model, allowing each side to scale, optimize, and choose storage engines independently.

In this lesson, you will master CQRS principles, synchronous command handling, asynchronous event-driven projections, and eventual consistency strategies.

---

## 1. CQRS architecture with PostgreSQL Elasticsearch

``` mermaid
flowchart TD
    subgraph ClientLayer["Client Applications"]
        WriteReq["Command: Create / Update Order"]
        ReadReq["Query: Search / View Orders Dashboard"]
    end

    subgraph CommandSide["Command (Write) Tier"]
        CommandController["OrderCommandController"]
        CommandService["OrderCommandService"]
        CommandDB[("PostgreSQL (3NF Normalized Write Model)")]
        
        CommandController --> CommandService
        CommandService -->|Enforce business rules & Commit| CommandDB
    end

    subgraph SyncTier["Asynchronous Synchronization Pipeline"]
        OutboxRelay["Transactional Outbox / Kafka Publisher"]
        KafkaTopic["Kafka Topic: 'order-events'"]
        ProjectionWorker["OrderQueryProjection (Kafka Consumer)"]
        
        CommandDB -.-> OutboxRelay
        OutboxRelay --> KafkaTopic
        KafkaTopic --> ProjectionWorker
    end

    subgraph QuerySide["Query (Read) Tier"]
        ProjectionWorker -->|Materialize Denormalized Document| ReadStore
        ReadStore[("Elasticsearch / Redis / MongoDB (Flattened Read Store)")]
        QueryController["OrderQueryController"]
        QueryService["OrderQueryService"]
        
        QueryController --> QueryService
        QueryService -->|Sub-millisecond query| ReadStore
    end

    WriteReq --> CommandController
    ReadReq --> QueryController
```

---

## 2. Command vs query responsibility matrix

| Dimension | Command Model (Writes) | Query Model (Reads) |
| :--- | :--- | :--- |
| **Primary Goal** | Data integrity, transactional consistency, business invariant validation. | High throughput, sub-millisecond latency, zero JOIN complexity. |
| **Operations** | `CreateOrderCommand`, `CancelOrderCommand`. | `GetOrderByIdQuery`, `SearchOrdersQuery`. |
| **Data Schema** | Highly normalized (3NF) in PostgreSQL/MySQL. | Denormalized, pre-aggregated JSON documents in Elasticsearch/Redis. |
| **Scaling Strategy** | Scaled via sharding, partition keys, or vertical memory. | Horizontally scaled read-replicas with aggressive caching. |
| **Consistency** | Strong ACID consistency. | Eventual consistency (projections lag by 5-50ms). |

---

## 3. Command side implementation (Spring Boot)

```java
package com.example.command;

import com.example.events.OrderCreatedEvent;
import com.example.model.Order;
import com.example.repository.OrderRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class OrderCommandService {

    private final OrderRepository orderRepository;
    private final KafkaTemplate<String, Object> kafkaTemplate;

    public record CreateOrderCommand(String customerId, double totalAmount, String shippingAddress) {}

    @Transactional
    public Long handleCreateOrder(CreateOrderCommand cmd) {
        // Enforce business rules & validation
        if (cmd.totalAmount() <= 0) {
            throw new IllegalArgumentException("Order amount must be positive");
        }

        Order order = new Order(cmd.customerId(), cmd.totalAmount(), cmd.shippingAddress());
        Order saved = orderRepository.save(order);

        // Emit integration event to synchronize the Query read model
        OrderCreatedEvent event = new OrderCreatedEvent(
                saved.getId(),
                saved.getCustomerId(),
                saved.getTotalAmount(),
                saved.getShippingAddress(),
                saved.getCreatedAt()
        );
        kafkaTemplate.send("order-events", saved.getId().toString(), event);
        log.info("Command executed: Order {} persisted to write model", saved.getId());

        return saved.getId();
    }
}
```

---

## 4. Query side projection read model

### 1. Asynchronous projection consumer

```java
package com.example.query.projection;

import com.example.events.OrderCreatedEvent;
import com.example.query.document.OrderReadDocument;
import com.example.query.repository.OrderSearchRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class OrderQueryProjection {

    private final OrderSearchRepository searchRepository;

    /**
     * Consumes domain event and materializes a denormalized read document
     */
    @KafkaListener(topics = "order-events", groupId = "cqrs-read-projection-group")
    public void projectOrderCreated(OrderCreatedEvent event) {
        log.info("Projecting Order {} into Elasticsearch Read Store", event.orderId());

        OrderReadDocument doc = OrderReadDocument.builder()
                .id(event.orderId().toString())
                .customerId(event.customerId())
                .totalAmount(event.totalAmount())
                .shippingAddress(event.shippingAddress())
                .status("COMPLETED")
                .createdAt(event.createdAt())
                .build();

        searchRepository.save(doc); // Instant write to denormalized read index
    }
}
```

### 2. High-performance query service

```java
package com.example.query.service;

import com.example.query.document.OrderReadDocument;
import com.example.query.repository.OrderSearchRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class OrderQueryService {

    private final OrderSearchRepository searchRepository;

    public OrderReadDocument getOrderById(String id) {
        return searchRepository.findById(id)
                .orElseThrow(() -> new RuntimeException("Order not found in search index: " + id));
    }

    public List<OrderReadDocument> searchOrdersByCustomer(String customerId) {
        return searchRepository.findByCustomerIdOrderByCreatedAtDesc(customerId);
    }
}
```

---

## 5. Mitigating eventual consistency in UI

Because query projections update asynchronously over Kafka, a user who clicks "Submit Order" and immediately redirects to the "Order List" might experience a temporary 20ms read miss.

**Production Mitigations**:
1. **Optimistic UI Updates**: The frontend immediately adds the submitted order to its local React/Vue state before the server read index catches up.
2. **WebSocket / SSE Notification**: The server pushes a notification when the query projection is indexed.
3. **Read-Your-Own-Writes Fallback**: For the first 2 seconds after creation, direct queries check the primary write database if absent in the read index.

---

## 6. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **CQRS Frameworks** | Custom Kafka event listeners or Axon Framework 4.x integration. | Native Spring Data multi-store projections with automated CDC replication. |
| **Search Engine Client** | Spring Data Elasticsearch using modern Elasticsearch Java Client 8.x. | Vector-native hybrid full-text and semantic embedding search projections. |
| **Reactive Projections** | Reactive Kafka consumers updating Project Reactor sinks. | Continuous streaming query projections over HTTP/3 server push. |

---

## 7. Primary sources and further reading

- [CQRS Pattern, Martin Fowler](https://martinfowler.com/bliki/CQRS.html), The seminal article on command and query separation.
- [Microservices Patterns: CQRS, Chris Richardson](https://microservices.io/patterns/data/cqrs.html).
- [Axon Framework Documentation](https://docs.axoniq.io/), Enterprise CQRS and Event Sourcing engine for Java.

---

## 8. Knowledge check and practice

??? question "Question 1: What is the fundamental principle behind CQRS?"
    **Answer**: Separating the data model and storage engine for write operations (commands) from read operations (queries) to optimize each independently.

??? question "Question 2: What is an Event-Driven Projection in CQRS?"
    **Answer**: A background consumer that listens to domain events from the command side and updates denormalized view documents in the query datastore.

??? question "Question 3: How does CQRS improve read performance under high scale?"
    **Answer**: By pre-computing and flattening data into dedicated read stores (like Elasticsearch or Redis), eliminating expensive multi-table SQL JOINs during user queries.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0065: Guaranteed Message Delivery: Transactional Outbox Pattern**](0065-transactional-outbox-pattern-postgres-kafka.md) | [**All Lessons**](index.md) | [ **0067: Distributed Idempotency with Redis SETNX**](0067-distributed-idempotency-redis-setnx.md) |

🎉 **Lesson 0066 completed! Proceed to Lesson 0067 to master distributed idempotency and duplicate request prevention.**
