---
icon: lucide/bug
---

# Troubleshooting Hibernate N+1 queries and `LazyInitializationException`

Two frequent production defects in Spring Boot applications using JPA/Hibernate are undetected N+1 query storms and `org.hibernate.LazyInitializationException: could not initialize proxy - no Session`.

Here is how to diagnose and fix both problems.

---

## 1. Issue 1: `LazyInitializationException: could not initialize proxy - no Session`

### Symptoms
When serializing an entity in the controller layer or accessing a lazy relationship outside of a `@Transactional` service boundary, the application crashes with:

```text
org.hibernate.LazyInitializationException: could not initialize proxy [com.example.demo.domain.Customer#101] - no Session
    at org.hibernate.proxy.AbstractLazyInitializer.initialize(AbstractLazyInitializer.java:165)
    at org.hibernate.proxy.AbstractLazyInitializer.getImplementation(AbstractLazyInitializer.java:314)
    at com.example.demo.domain.Customer$HibernateProxy$abc.getName(Unknown Source)
    at com.example.demo.controller.OrderController.getOrder(OrderController.java:34)
```

### Root cause architecture

``` mermaid
sequenceDiagram
    autonumber
    actor Client as HTTP Client
    participant Controller as OrderController (Non-Transactional)
    participant Service as OrderService (@Transactional)
    participant PC as Persistence Context (Session)
    participant DB as PostgreSQL

    Client->>Controller: GET /api/orders/42
    Controller->>Service: getOrderById(42)
    Note over Service,PC: Transaction Starts -> Session Opened
    Service->>PC: em.find(Order.class, 42)
    PC->>DB: SELECT * FROM orders WHERE id = 42
    DB-->>PC: Order row (customer_id = 101)
    Note over PC: Injects ByteBuddy CGLIB Proxy for Customer
    PC-->>Service: Managed Order Entity
    Note over Service,PC: Transaction Commits -> Session CLOSED
    Service-->>Controller: Returns Detached Order Entity

    Controller->>Controller: order.getCustomer().getName()
    Note over Controller: Customer is an uninitialized proxy.<br/>Session is already CLOSED.<br/>Throws LazyInitializationException.
    Controller-->>Client: 500 Internal Server Error
```

---

### The OSIV trap (`spring.JPA.open-in-view=true`)

Many tutorials recommend setting `spring.jpa.open-in-view=true`. Avoid this in production.
- **Why OSIV is dangerous**: It holds database connections open across the entire HTTP request cycle, including template rendering, JSON serialization, and slow client network transfers. Under moderate traffic, connection pools (HikariCP) exhaust quickly, bringing down the service.

---

### Production resolutions

#### Solution A: JPQL `JOIN FETCH`
Fetch the necessary relationships inside the service boundary:
```java
@Query("SELECT o FROM Order o JOIN FETCH o.customer WHERE o.id = :id")
Optional<Order> findByIdWithCustomer(@Param("id") Long id);
```

#### Solution B: DTO projections (Recommended)
Map the required fields directly into a record DTO within the `@Transactional` boundary:
```java
@Transactional(readOnly = true)
public OrderResponse getOrderById(Long id) {
    Order order = orderRepository.findByIdWithCustomer(id)
        .orElseThrow(() -> new ResourceNotFoundException("Order not found: " + id));
    return new OrderResponse(order.getId(), order.getOrderNumber(), order.getCustomer().getName());
}
```

---

## 2. Issue 2: Silent N+1 query storms

### Symptoms
Database CPU spikes to 100%, latency climbs to several seconds, and HikariCP connection timeouts occur under load.

### Enabling diagnostic SQL logging

To expose hidden N+1 queries in development, add the following to `application.yml`:

```yaml
logging:
  level:
    org.hibernate.SQL: DEBUG
    org.hibernate.orm.jdbc.bind: TRACE # Shows parameter values in Hibernate 6
spring:
  jpa:
    properties:
      hibernate:
        format_sql: true
        generate_statistics: true # Prints query execution count and metrics
```

### Diagnostic output example
```text
DEBUG org.hibernate.SQL: SELECT o.id, o.order_number FROM orders o
DEBUG org.hibernate.SQL: SELECT c.id, c.name FROM customers c WHERE c.id = ?
DEBUG org.hibernate.SQL: SELECT c.id, c.name FROM customers c WHERE c.id = ?
DEBUG org.hibernate.SQL: SELECT c.id, c.name FROM customers c WHERE c.id = ?
... (Repeated 200 times for 200 orders)
```

---

### Diagnostic flowchart and resolution matrix

``` mermaid
flowchart TD
    Problem["N+1 Query Detected"] --> CheckType{"Single entity association or collection?"}
    
    CheckType -->|Single @ManyToOne| Solution1["Use JOIN FETCH in JPQL<br/>or @EntityGraph(attributePaths={'customer'})"]
    CheckType -->|Multiple Child @OneToMany| Solution2["Use @BatchSize(size = 30)<br/>on child collection to avoid Cartesian product"]
    CheckType -->|Read-only API reporting| Solution3["Use Record DTO Constructor Projection<br/>(SELECT new OrderSummaryDto(...))"]
```

---

## Navigation and debugging index

| Previous | Debugging index | Next |
| :--- | :---: | ---: |
| [**Troubleshooting REST API exceptions**](rest-validation-exception-debugging.md) | [**All debugging guides**](index.md) | [**Transaction rollback and proxy pitfalls**](transaction-rollback-and-proxy-pitfalls.md) |
