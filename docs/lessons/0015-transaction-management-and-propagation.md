---
icon: lucide/shield-check
---

# 0015: Transaction Management: @Transactional, Proxy Mechanics, Propagation & Isolation Levels

In distributed and high-concurrency systems, maintaining **data consistency** across multi-step database mutations is paramount. Spring provides declarative transaction management via `@Transactional`, but treating it as a black box leads to silent data corruption, unrolled rollbacks, and locking deadlocks.

In this lesson, you will dissect how `@Transactional` operates via **AOP proxies**, avoid the **Self-Invocation Trap**, configure **Propagation Strategies** (`REQUIRED` vs `REQUIRES_NEW`), and tune **Database Isolation Levels** to prevent concurrency anomalies.

---

## 1. How `@Transactional` Operates Under the Hood

Spring does not alter bytecode or talk directly to the database driver at compile time. Instead, Spring wraps your bean in a **Dynamic Proxy** using Spring AOP:

``` mermaid
sequenceDiagram
    autonumber
    actor Client as OrderController
    participant Proxy as OrderService (CGLIB Proxy)
    participant Interceptor as TransactionInterceptor
    participant TxManager as JpaTransactionManager
    participant Target as OrderServiceImpl (Target Bean)
    participant DB as PostgreSQL

    Client->>Proxy: placeOrder(OrderRequest)
    Proxy->>Interceptor: invoke()
    Interceptor->>TxManager: getTransaction() (Begin TX)
    TxManager->>DB: SET autocommit = 0, BEGIN TRANSACTION
    
    Interceptor->>Target: placeOrder(OrderRequest)
    Note over Target: Business logic executes.<br/>Database mutations performed.
    
    alt Successful Execution
        Target-->>Interceptor: Returns OrderResponse
        Interceptor->>TxManager: commit()
        TxManager->>DB: COMMIT
        Interceptor-->>Client: Success Response
    else Exception Thrown (RuntimeException)
        Target-->>Interceptor: throws PaymentFailedException
        Interceptor->>TxManager: rollback()
        TxManager->>DB: ROLLBACK
        Interceptor-->>Client: Propagates Exception
    end
```

---

## 2. The Self-Invocation Trap (Why `@Transactional` Silently Fails)

The most infamous pitfall in Spring development is calling a `@Transactional` method from another method **within the same class**:

```java
@Service
public class OrderService {

    // ❌ NON-TRANSACTIONAL METHOD
    public void processOrderBatch(List<OrderRequest> requests) {
        for (OrderRequest req : requests) {
            // ❌ SELF-INVOCATION: Calls 'this.createSingleOrder()' directly!
            // Bypasses the Spring CGLIB Proxy! No transaction is ever started!
            createSingleOrder(req);
        }
    }

    @Transactional
    public void createSingleOrder(OrderRequest req) {
        // DB mutations here will NOT be wrapped in a transaction!
    }
}
```

``` mermaid
flowchart TD
    Caller["Caller"] --> Proxy["Spring Proxy<br/><i>(TransactionInterceptor)</i>"]
    Proxy -->|"Intercepts"| M1["methodA()<br/><i>(@Transactional)</i>"]
    M1 -->|"❌ this.methodB()<br/>Bypasses Proxy!"| M2["methodB()<br/><i>(@Transactional ignored!)</i>"]
```

### The Solutions:
1. **Move the method to a separate `@Service` bean** (Recommended for clean architecture).
2. **Self-inject the bean** via constructor or `@Lazy` injection and invoke through the injected reference (`orderService.createSingleOrder(req)`).

---

## 3. Rollback Mechanics: Checked vs Unchecked Exceptions

By default in Spring:
- **Unchecked Exceptions** (subclasses of `RuntimeException` and `Error`) trigger an automatic **ROLLBACK**.
- **Checked Exceptions** (subclasses of `Exception`, like `IOException`, `SQLException`) **DO NOT** trigger a rollback! The transaction commits anyway!

```java
// ❌ DANGEROUS: If FileNotFoundException occurs, database changes STILL COMMIT!
@Transactional
public void importData() throws IOException {
    userRepository.save(new User(...));
    readFile(); // Throws IOException -> Transaction COMMITS!
}

// ✅ SECURE: Explicitly configure rollbackFor
@Transactional(rollbackFor = Exception.class)
public void importDataSafe() throws IOException {
    userRepository.save(new User(...));
    readFile(); // Throws IOException -> Transaction ROLLS BACK!
}
```

---

## 4. Transaction Propagation Levels

Propagation defines how transaction boundaries behave when a transactional method calls another transactional method.

| Propagation | Behavior | Primary Use Case |
| :--- | :--- | :--- |
| **`REQUIRED`** *(Default)* | Joins active transaction if one exists; creates a new one if none exists. | Standard CRUD service methods. |
| **`REQUIRES_NEW`** | Always creates a **new, independent transaction**, suspending the existing transaction if present. | Audit logging, notification history, billing records that must persist even if outer transaction rolls back. |
| **`NESTED`** | Executes within a nested transaction using **JDBC Savepoints**. Rolls back to savepoint without affecting outer transaction. | Sub-tasks with fallback recovery. |
| **`MANDATORY`** | Must run within an existing transaction. Throws `IllegalTransactionStateException` if none exists. | Internal repository helper logic. |
| **`SUPPORTS`** | Runs within a transaction if one exists; executes non-transactionally if none exists. | Read-only operations. |
| **`NOT_SUPPORTED`** | Suspends current transaction and executes non-transactionally. | Long-running I/O or external HTTP calls. |
| **`NEVER`** | Throws exception if an active transaction exists. | Strict non-transactional operations. |

### Real-World Example: Audit Logging with `REQUIRES_NEW`

```java
@Service
public class OrderService {

    private final AuditService auditService;
    private final OrderRepository orderRepository;

    @Transactional
    public void placeOrder(OrderRequest request) {
        try {
            // If payment fails, placeOrder rolls back
            processPayment(request);
            orderRepository.save(new Order(request));
        } catch (PaymentException ex) {
            // ✅ Audit record MUST persist even though outer order transaction fails!
            auditService.logFailure(request.getUserId(), ex.getMessage());
            throw ex;
        }
    }
}

@Service
public class AuditService {
    
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void logFailure(Long userId, String reason) {
        // Runs in a dedicated transaction; commits independently of caller!
        auditRepository.save(new AuditLog(userId, reason, Instant.now()));
    }
}
```

---

## 5. Database Isolation Levels & Concurrency Anomalies

Isolation levels prevent data anomalies when multiple transactions execute concurrently:

### Concurrency Anomalies:
1. **Dirty Read**: Transaction A reads uncommitted modifications made by Transaction B (which may later roll back).
2. **Non-Repeatable Read**: Transaction A reads a row, Transaction B updates/commits that row, Transaction A reads it again and sees different values.
3. **Phantom Read**: Transaction A queries a range of rows, Transaction B inserts/commits new matching rows, Transaction A re-queries and sees "phantom" rows.

### Isolation Level vs Anomaly Matrix:

| Isolation Level | Dirty Read | Non-Repeatable Read | Phantom Read | Typical DB Default |
| :--- | :---: | :---: | :---: | :---: |
| **`READ_UNCOMMITTED`** | ❌ Allowed | ❌ Allowed | ❌ Allowed | — |
| **`READ_COMMITTED`** | 🛡️ Prevented | ❌ Allowed | ❌ Allowed | PostgreSQL, Oracle, SQL Server |
| **`REPEATABLE_READ`** | 🛡️ Prevented | 🛡️ Prevented | ❌ / 🛡️ (MVCC) | MySQL (InnoDB) |
| **`SERIALIZABLE`** | 🛡️ Prevented | 🛡️ Prevented | 🛡️ Prevented | — (Highest lock contention) |

```java
@Transactional(isolation = Isolation.SERIALIZABLE)
public void executeCriticalFinancialTransfer(Long fromId, Long toId, BigDecimal amount) {
    // Ensures total mathematical consistency, eliminating phantom reads & write skew
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4: Transaction Architecture Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        TLTransaction["ThreadLocal TransactionSynchronizationManager"]
        PlatformTM["PlatformTransactionManager Hierarchy"]
        SeparateReactive["Separate ReactiveTransactionManager"]
    end

    subgraph SB4["Spring Boot 4.x"]
        ScopedValTx["ScopedValue Transaction Context (Loom Native)"]
        UnifiedTM["Unified Transaction Pipeline Coordinator"]
        ZeroLeakVirtual["Zero-Leak Virtual Thread Synchronization"]
    end

    SB3 ==>|Loom Concurrency Modernization| SB4
```

### Key Differences & Configuration Comparison

| Transaction Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Context Storage Engine** | `ThreadLocal` storage map in `TransactionSynchronizationManager`. | **Java 21+ `ScopedValue` Context**: Immutable, lightweight, zero-leak transaction context binding across millions of Virtual Threads. |
| **Virtual Thread Safety** | Susceptible to memory overhead if `TransactionSynchronizationManager` cleanup fails in deeply nested forks. | **Native Structured Concurrency Support**: Transactions propagate safely into sub-tasks via `StructuredTaskScope`. |
| **Reactive & Relational Bridge** | Strict split between `PlatformTransactionManager` (JDBC/JPA) and `ReactiveTransactionManager` (R2DBC). | **Unified Transaction SPI**: Seamless coordination across relational and reactive database drivers. |

---

## 7. Primary Sources & Further Reading

- [Spring Framework Reference: Transaction Management](https://docs.spring.io/spring-framework/reference/data-access/transaction.html) — Core reference on AOP proxies and `PlatformTransactionManager`.
- [Vlad Mihalcea: Spring @Transactional Rules and Pitfalls](https://vladmihalcea.com/spring-transactional-rules-and-pitfalls/) — In-depth analysis of proxy self-invocation and rollback traps.
- [PostgreSQL Documentation: Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html) — How relational engines implement MVCC and isolation levels.

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: Why does calling `@Transactional methodB()` from `methodA()` in the same class fail to initiate a transaction?"
    **Answer**: Internal method calls use the standard `this` pointer in Java heap memory, bypassing the Spring AOP dynamic proxy (`TransactionInterceptor`) that manages transaction boundaries.

??? question "Question 2: What exception types trigger a rollback by default in Spring `@Transactional`?"
    **Answer**: Only unchecked exceptions (`RuntimeException` and `Error`). Checked exceptions do not trigger rollbacks unless explicitly declared via `@Transactional(rollbackFor = Exception.class)`.

??? question "Question 3: When should you use `Propagation.REQUIRES_NEW`?"
    **Answer**: When an operation (such as security auditing, failure logging, or billing tokens) must commit its database changes independently, even if the surrounding outer transaction fails and rolls back.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0014: Entity Relationships & N+1 Problem**](0014-entity-relationships-lazy-loading-n-plus-1.md) | [**All Lessons**](index.md) | [➡️ **0016: Multi-DataSource & NoSQL Integration**](0016-multi-datasource-and-nosql-integration.md) |
