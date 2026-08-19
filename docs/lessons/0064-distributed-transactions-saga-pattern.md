---
icon: lucide/refresh-cw
---

# 0064: Distributed transactions: Saga pattern with Kafka choreography

In a monolithic application, maintaining data consistency is straightforward: wrap operations inside `@Transactional` and let the relational database commit or roll back via ACID guarantees. In a microservices architecture with a **database-per-service** model, a single business workflow (such as customer checkout) spans Order, Inventory, Payment, and Shipping services across separate databases.

Two-Phase Commit (2PC / XA) is a distributed anti-pattern because holding cross-network database locks leads to catastrophic latency and deadlocks.

The **SAGA Pattern** manages distributed transactions as a series of independent local transactions. If any step fails, the SAGA coordinates **Compensating Transactions** to undo previously completed steps and maintain eventual consistency.

In this lesson, you will master SAGA Choreography using Apache Kafka event streams, implementing forward actions, and executing compensating rollbacks.

---

## 1. Saga choreography execution flow

``` mermaid
flowchart TD
    subgraph HappyPath["Forward Transaction Sequence (Success)"]
        S1["1. Order Service: Create Order (Status: PENDING)"]
        E1["Emit 'OrderCreatedEvent'"]
        S2["2. Inventory Service: Reserve Stock"]
        E2["Emit 'InventoryReservedEvent'"]
        S3["3. Payment Service: Charge Card"]
        E3["Emit 'PaymentSuccessEvent'"]
        S4["4. Order Service: Approve Order (Status: COMPLETED)"]

        S1 --> E1 --> S2 --> E2 --> S3 --> E3 --> S4
    end

    subgraph RollbackPath["Compensating Rollback Sequence (Payment Failed)"]
        F1["3b. Payment Service: Insufficient Funds"]
        EF1["Emit 'PaymentFailedEvent'"]
        C1["4b. Inventory Service: Release Reserved Stock (Compensating)"]
        C2["5b. Order Service: Mark Order CANCELLED (Compensating)"]

        F1 --> EF1 --> C1 --> C2
    end

    HappyPath ~~~ RollbackPath
```

---

## 2. Choreography vs orchestration

| Dimension | SAGA Choreography (Event-Driven) | SAGA Orchestration (Command-Driven) |
| :--- | :--- | :--- |
| **Coordination Model** | Decentralized: Services listen to Kafka events and react autonomously. | Centralized: A dedicated Orchestrator service commands participants. |
| **Coupling** | Loosely coupled through integration event schemas. | Participants coupled to the Orchestrator's command contract. |
| **Complexity** | Simple for 2-4 services; harder to trace as participants grow. | Easy to inspect and monitor central workflow state; higher initial setup. |
| **Failure Point** | No single coordinator bottleneck. | Orchestrator service must be highly available. |

---

## 3. Spring Boot Kafka choreography implementation

### Step 1: Order service (initiating Saga listening for results)

```java
package com.example.orderservice.service;

import com.example.events.OrderCreatedEvent;
import com.example.events.PaymentFailedEvent;
import com.example.events.PaymentSuccessEvent;
import com.example.orderservice.model.Order;
import com.example.orderservice.model.OrderStatus;
import com.example.orderservice.repository.OrderRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class OrderSagaManager {

    private final OrderRepository orderRepository;
    private final KafkaTemplate<String, Object> kafkaTemplate;

    @Transactional
    public Order createOrder(String customerId, double totalAmount) {
        Order order = orderRepository.save(new Order(customerId, totalAmount, OrderStatus.PENDING));
        
        // Publish trigger event to Kafka
        kafkaTemplate.send("order-events", order.getId(), new OrderCreatedEvent(order.getId(), customerId, totalAmount));
        log.info("SAGA Started: Order {} created in PENDING state", order.getId());
        return order;
    }

    @Transactional
    @KafkaListener(topics = "payment-events", groupId = "order-saga-group")
    public void handlePaymentResult(Object event) {
        if (event instanceof PaymentSuccessEvent success) {
            log.info("SAGA Complete: Approving order {}", success.orderId());
            orderRepository.findById(success.orderId()).ifPresent(order -> order.setStatus(OrderStatus.COMPLETED));
        } else if (event instanceof PaymentFailedEvent failure) {
            log.warn("SAGA Compensating: Cancelling order {}", failure.orderId());
            orderRepository.findById(failure.orderId()).ifPresent(order -> order.setStatus(OrderStatus.CANCELLED));
        }
    }
}
```

---

### Step 2: Inventory service (forward action compensation listener)

```java
package com.example.inventoryservice.service;

import com.example.events.InventoryReservedEvent;
import com.example.events.OrderCreatedEvent;
import com.example.events.PaymentFailedEvent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class InventorySagaListener {

    private final KafkaTemplate<String, Object> kafkaTemplate;

    /**
     * Forward Step: Reserve items upon order creation
     */
    @Transactional
    @KafkaListener(topics = "order-events", groupId = "inventory-saga-group")
    public void handleOrderCreated(OrderCreatedEvent event) {
        log.info("Reserving stock for order: {}", event.orderId());
        
        // Execute local database update (deduct stock)
        boolean stockReserved = true; 

        if (stockReserved) {
            kafkaTemplate.send("inventory-events", event.orderId(), new InventoryReservedEvent(event.orderId()));
        }
    }

    /**
     * Compensating Transaction: Roll back stock reservation if payment fails
     */
    @Transactional
    @KafkaListener(topics = "payment-events", groupId = "inventory-saga-group")
    public void handlePaymentFailure(Object event) {
        if (event instanceof PaymentFailedEvent failure) {
            log.warn("COMPENSATING ACTION: Releasing reserved stock for order {}", failure.orderId());
            // Restore inventory count in database
        }
    }
}
```

---

## 4. Key rules for reliable Saga systems

> [!IMPORTANT]
> 1. **Compensating Transactions Must Never Fail**: If a compensating action fails due to transient database issues, it must retry indefinitely until succeeded or route to an alert queue.
> 2. **Idempotency is Mandatory**: Because Kafka guarantees at-least-once delivery, event listeners must track processed event IDs in an idempotency table to prevent duplicate compensations.
> 3. **Semantic Locks**: Mark domain entities with status flags (e.g., `PENDING_CANCELLATION`, `RESERVED`) to warn other concurrent threads that a SAGA is in progress.

---

## 5. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **SAGA Orchestration** | Implemented using custom state machines or Camunda/Temporal engines. | Native declarative SAGA DSL with automated compensation rollbacks. |
| **Event Persistence** | Spring Modulith Transactional Event Publication for intra-module SAGAs. | Integrated cross-cluster distributed event state store. |
| **Tracing Correlation** | Tracing context manually carried in Kafka event headers. | OTel distributed SAGA trace graphs with automatic compensation span tagging. |

---

## 6. Primary sources and further reading

- [Microservices Patterns: SAGA Pattern, Chris Richardson](https://microservices.io/patterns/data/saga.html).
- [Designing Data-Intensive Applications, Martin Kleppmann](https://dataintensive.net/), Distributed consistency models and atomic commit protocols.
- [Enterprise Integration Patterns: Compensating Transaction](https://www.enterpriseintegrationpatterns.com/).

---

## 7. Knowledge check and practice

??? question "Question 1: Why is Two-Phase Commit (2PC) discouraged in modern microservices?"
    **Answer**: 2PC holds blocking cross-network database locks that increase latency, reduce availability, create single points of failure, and tightly couple independent service databases.

??? question "Question 2: What is the role of a Compensating Transaction in the SAGA pattern?"
    **Answer**: It acts as a semantic rollback that undoes the business effects of a previously committed local transaction when a subsequent step in the SAGA workflow fails.

??? question "Question 3: What is the main difference between SAGA Choreography and SAGA Orchestration?"
    **Answer**: Choreography is decentralized (services react autonomously to domain events), while Orchestration uses a central coordinator that explicitly commands services to execute actions.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0063: Fault Tolerance with Resilience4j**](0063-fault-tolerance-resilience4j.md) | [**All Lessons**](index.md) | [ **0065: Guaranteed Message Delivery: Transactional Outbox Pattern**](0065-transactional-outbox-pattern-postgres-kafka.md) |

🎉 **Lesson 0064 completed! Proceed to Lesson 0065 to master guaranteed zero-loss event publishing with the Transactional Outbox Pattern.**
