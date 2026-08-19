---
icon: lucide/git-merge
---

# 0014: Entity relationships (1:1, 1:N, N:N), fetch types, and N+1 query troubleshooting

In relational data modeling, entities do not exist in isolation. They connect through foreign keys, junction tables, and parent-child hierarchies. In JPA and Hibernate, mapping these relationships incorrectly is the single most common cause of catastrophic database performance degradation.

In this lesson, you will master **Entity Relationships**, bidirectional synchronization, **Cascade Types vs Orphan Removal**, the dangerous default **Fetch Types**, and how to identify and eradicate the **N+1 Query Problem**.

---

## 1. The 4 JPA relationship mappings

JPA provides four core annotations to represent database associations:

``` mermaid
erDiagram
    CUSTOMER ||--o{ ORDER : "places (1:N)"
    ORDER ||--|{ ORDER_ITEM : "contains (1:N)"
    USER ||--|| USER_PROFILE : "has (1:1)"
    STUDENT }|--|{ COURSE : "enrolls (N:N)"
```

| Annotation | Description | Default FetchType in JPA | Best Practice FetchType |
| :--- | :--- | :---: | :---: |
| **`@ManyToOne`** | Child referencing parent (e.g. `Order -> Customer`) | ⚠️ `EAGER` | **`LAZY`** (Always override!) |
| **`@OneToOne`** | 1-to-1 association (e.g. `User <-> UserProfile`) | ⚠️ `EAGER` | **`LAZY`** (Always override!) |
| **`@OneToMany`** | Parent holding collection of children (e.g. `Customer -> Orders`) | ✅ `LAZY` | `LAZY` |
| **`@ManyToMany`** | Junction/join table (e.g. `Student <-> Course`) | ✅ `LAZY` | `LAZY` |

!!! caution "CRITICAL JPA TRAP: Eager Defaults"
    In the JPA specification, `@ManyToOne` and `@OneToOne` default to `FetchType.EAGER`. Whenever you fetch an entity, Hibernate will automatically issue immediate `LEFT OUTER JOIN`s or additional `SELECT` statements for all eager associations, even if your business logic never touches them.
    **Rule of Thumb**: Always explicitly declare `fetch = FetchType.LAZY` on **every** single relationship!

---

## 2. Bidirectional mapping relationship ownership

In a bidirectional relationship, one side must be the **Owning Side** and the other the **Inverse Side**:

- **Owning Side**: Contains the physical foreign key column (`@JoinColumn(name = "customer_id")`). Changes made here are written to the database.
- **Inverse (Non-Owning) Side**: Uses the `mappedBy` attribute referencing the Java field name on the owning side. Hibernate ignores changes made only to the inverse collection unless synchronized!

``` mermaid
classDiagram
    class Customer {
        -Long id
        -String name
        -List~Order~ orders
        +addOrder(Order)
        +removeOrder(Order)
    }
    class Order {
        -Long id
        -String orderNumber
        -Customer customer
    }
    Customer "1" *-- "many" Order : mappedBy = "customer"<br/>(Inverse Side)
    Order --> Customer : @JoinColumn(customer_id)<br/>(Owning Side)
```

### Writing bidirectional helper synchronization methods

To prevent memory-state desynchronization where an `Order` references a `Customer`, but `customer.getOrders()` doesn't contain the order:

```java
@Entity
@Table(name = "customers")
@Getter @Setter @NoArgsConstructor
public class Customer {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String name;

    @OneToMany(mappedBy = "customer", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Order> orders = new ArrayList<>();

    // ✅ Defensive synchronization helpers
    public void addOrder(Order order) {
        orders.add(order);
        order.setCustomer(this);
    }

    public void removeOrder(Order order) {
        orders.remove(order);
        order.setCustomer(null);
    }
}
```

---

## 3. Cascade types vs `orphanRemoval`

- **`CascadeType.PERSIST` / `CascadeType.ALL`**: Propagates entity operations from parent to child. Calling `em.persist(customer)` automatically persists all items in `customer.getOrders()`.
- **`orphanRemoval = true`**: If a child entity is removed from the parent's collection (`customer.getOrders().remove(0)`), Hibernate marks that child entity as `REMOVED` and deletes its row from the database upon flush.

---

## 4. The dreaded n1 query problem

The **N+1 Problem** occurs when an application loads $N$ parent records in 1 query, and then iterates over them accessing a lazy relationship, triggering $N$ additional queries to fetch the children.

``` mermaid
sequenceDiagram
    autonumber
    actor App as OrderService
    participant Hibernate as Hibernate ORM
    participant DB as PostgreSQL Database

    Note over App,DB: The 1 Initial Query
    App->>Hibernate: orderRepository.findAll()
    Hibernate->>DB: Query 1: SELECT * FROM orders (Returns 100 Orders)
    DB-->>Hibernate: 100 Order Records

    Note over App,DB: The N Subsequent Queries in a Loop!
    loop For Each of the 100 Orders
        App->>Hibernate: order.getCustomer().getName()
        Hibernate->>DB: Query 2..101: SELECT * FROM customers WHERE id = ?
        DB-->>Hibernate: Customer Record
    end
    Note over App,DB: Result: 1 + 100 = 101 Total Network Roundtrips!
```

If you have 1,000 orders, you just hammered your database with **1,001 separate queries** for a single HTTP request!

---

## 5. How to fix the n1 problem

There are three primary production-tested solutions to eliminate N+1 queries:

### Solution 1: JPQL `JOIN fetch (explicit eager join)

`JOIN FETCH` instructs Hibernate to retrieve both the parent entity and the related child entity in a single SQL `INNER JOIN` or `LEFT JOIN`:

```java
public interface OrderRepository extends JpaRepository<Order, Long> {

    @Query("SELECT o FROM Order o JOIN FETCH o.customer WHERE o.status = :status")
    List<Order> findAllWithCustomerByStatus(@Param("status") OrderStatus status);
}
```
**Generated SQL**:
```sql
SELECT o.id, o.order_number, o.status, c.id, c.name, c.email
FROM orders o
INNER JOIN customers c ON o.customer_id = c.id
WHERE o.status = 'COMPLETED';
```
*(Executes exactly 1 single query instead of 1 + N!)*

---

### Solution 2: Spring data `@EntityGraph`

`@EntityGraph` dynamically overrides lazy fetching at query time without rewriting custom JPQL:

```java
public interface OrderRepository extends JpaRepository<Order, Long> {

    // Overrides default lazy fetch to eagerly fetch 'customer' and 'items'
    @EntityGraph(attributePaths = {"customer", "items"})
    List<Order> findByStatus(OrderStatus status);
}
```

---

### Solution 3: Hibernate `@BatchSize` (batched in-clause loading)

When fetching collections across complex graphs where `JOIN FETCH` would cause a Cartesian Product (MultipleBagFetchException), annotate the collection with `@BatchSize`:

```java
@Entity
public class Customer {

    @OneToMany(mappedBy = "customer")
    @org.hibernate.annotations.BatchSize(size = 30)
    private List<Order> orders = new ArrayList<>();
}
```
Hibernate will batch lazy loading into `IN` clauses:
```sql
SELECT * FROM orders WHERE customer_id IN (?, ?, ?, ... 30 IDs);
```
*(Reduces 1,000 queries down to ~34 queries).*

---

## 6. Comparison of n1 mitigation strategies

``` mermaid
flowchart TD
    Choice{"How to resolve N+1?"}
    Choice -->|Single relationship join| JF["🚀 JPQL JOIN FETCH<br/>1 query, exact join control"]
    Choice -->|Dynamic query override| EG["💎 Spring @EntityGraph<br/>Clean derived method override"]
    Choice -->|Multiple child collections| BS["📦 Hibernate @BatchSize<br/>Avoids Cartesian Multi-Bag Exception"]
    Choice -->|Read-only API response| DTO["⚡ DTO Constructor Projection<br/>Zero entity overhead"]
```

---

## 7. Spring Boot 3 vs Spring Boot 4: Fetching optimization evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        ManualN1Audit["Manual datasource-proxy / QuickPerf N+1 Detection"]
        BatchSizeAnnotation["Explicit @BatchSize on Entity Collections"]
        RuntimeFetchPlan["Dynamic Runtime SQM Query Translation"]
    end

    subgraph SB4["Spring Boot 4.x"]
        AutoBatchSubquery["Auto-Subquery In-Clause Batch Fetching"]
        StaticFetchGraph["Compile-Time Fetch Graph Verification"]
        H7QueryPlan["Hibernate 7 Zero-Alloc Query Plan Cache"]
    end

    SB3 ==>|Query Optimization| SB4
```

### Key differences and configuration comparison

| Fetching Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Batch Fetching Mode** | Required explicit `@BatchSize` or `hibernate.default_batch_fetch_size`. | **Proactive Subquery Batching**: Uses subselect batch fetching by default on bulk queries. |
| **N+1 Diagnostic Tooling** | Relied on third-party log sniffers (`datasource-proxy`, `p6spy`). | **Built-in Actuator N+1 Metric Counters**: Surfaces anomalous query-per-request spikes directly to Micrometer. |
| **Query Plan Caching** | SQM query plan cache created allocation pressure under high QPS. | **Hibernate 7 Pre-Compiled AST**: Near-zero heap allocations during repeated parameter binding. |

---

## 8. Primary sources and further reading

- [Hibernate ORM User Guide: Fetching Strategies](https://docs.jboss.org/hibernate/orm/current/userguide/html_single/Hibernate_User_Guide.html#fetching), Official guide on dynamic vs static fetching.
- [Vlad Mihalcea: The N+1 Query Problem with JPA and Hibernate](https://vladmihalcea.com/n-plus-1-query-problem-jpa-hibernate/), Comprehensive diagnostics and solutions for N+1 queries.
- [Thorben Janssen: JPA 2.1 Entity Graph Explained](https://thorben-janssen.com/jpa-21-entity-graph-part-1-named-entity/), Named and dynamic entity graph strategies.

---

## 9. Knowledge check and practice

??? question "Question 1: Why does JPA's default `FetchType.EAGER` on `@ManyToOne` cause unexpected performance issues?"
    **Answer**: It automatically forces immediate SQL joins or secondary selects to fetch associated entities on every query, inflating memory consumption and database query count even when the association is not used.

??? question "Question 2: What is the fundamental cause of the N+1 query problem?"
    **Answer**: Loading a list of $N$ parent entities in 1 initial query and subsequently triggering $N$ separate queries when lazily accessing related child associations during iteration.

??? question "Question 3: How does JPQL `JOIN FETCH` resolve the N+1 problem?"
    **Answer**: It instructs the persistence provider to fetch the parent and related child entities simultaneously in a single SQL query using an SQL `JOIN`.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0013: Spring Data JPA: Repositories & Queries**](0013-spring-data-jpa-repositories-and-queries.md) | [**All Lessons**](index.md) | [ **0015: Transaction Management & Propagation**](0015-transaction-management-and-propagation.md) |
