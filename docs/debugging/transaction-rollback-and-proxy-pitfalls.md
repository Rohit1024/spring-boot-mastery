---
icon: lucide/bug
---

# Troubleshooting `@Transactional` Failures, Proxy Bypasses & Silent Rollback Errors

Declarative transaction management in Spring Boot via `@Transactional` provides high-level convenience, but subtle misunderstandings of **AOP Proxies**, **Exception Inheritance**, and **Transaction Propagation** often result in transactions that silently fail to roll back or fail to begin altogether.

This debugging playbook breaks down the top 4 transaction failure modes, diagnostic flows, and concrete fixes.

---

## 1. Failure Mode 1: The Proxy Self-Invocation Bypass

### The Symptom
Methods annotated with `@Transactional` execute database mutations, but when an exception occurs, no rollback is performed and no transaction boundary was ever created in SQL logs.

### Root Cause
Calling a method on the `this` reference inside the same class calls the raw Java instance directly, bypassing Spring's CGLIB proxy wrapper (`TransactionInterceptor`).

``` mermaid
flowchart TD
    Client["Client Caller"] --> Proxy["OrderService CGLIB Proxy<br/><i>(TransactionInterceptor)</i>"]
    Proxy -->|"1. Invokes"| Outer["bulkProcessOrders()<br/><i>(NO @Transactional)</i>"]
    Outer -->|"2. this.processSingleOrder()<br/>❌ Bypasses Proxy!"| Inner["processSingleOrder()<br/><i>(@Transactional IGNORED!)</i>"]
    Inner -->|"3. Throws RuntimeException"| DB["PostgreSQL<br/>⚠️ Mutations NOT rolled back!"]
```

### The Fix
Extract the transactional logic into a separate dedicated `@Service` bean:

```java
// ✅ BEST PRACTICE: Separate Service Bean
@Service
public class OrderBatchProcessor {
    private final SingleOrderService singleOrderService;

    public void processAll(List<OrderRequest> requests) {
        for (var req : requests) {
            singleOrderService.processTransactional(req); // Passes through proxy!
        }
    }
}

@Service
public class SingleOrderService {
    @Transactional
    public void processTransactional(OrderRequest req) {
        // Correctly intercepted and wrapped in a transaction!
    }
}
```

---

## 2. Failure Mode 2: Checked Exceptions Not Triggering Rollback

### The Symptom
A method throws a checked exception (such as `IOException`, `ParseException`, or a custom checked business exception), but the database still **commits** the partial data.

### Root Cause
By default, Spring's `RuleBasedTransactionAttribute` only rolls back on **Unchecked Exceptions** (`RuntimeException` and `Error`).

``` mermaid
sequenceDiagram
    autonumber
    participant App as Service Method
    participant Interceptor as TransactionInterceptor
    participant DB as PostgreSQL

    App->>DB: INSERT INTO users ...
    App-->>Interceptor: throws CustomCheckedException (extends Exception)
    Note over Interceptor: Is exception an instance of RuntimeException?<br/>❌ NO! It is a checked Exception.
    Interceptor->>DB: COMMIT (💥 Partial Data Persisted!)
```

### The Fix
Always declare `rollbackFor = Exception.class` on transactional business methods:

```java
@Transactional(rollbackFor = Exception.class)
public void processFinancialSettlement(Long batchId) throws SettlementCheckedException {
    // Both checked and unchecked exceptions will now trigger ROLLBACK
}
```

---

## 3. Failure Mode 3: Swallowed Exceptions in `try-catch`

### The Symptom
An exception occurs inside a helper call, you catch and log it, but the transaction still commits or throws an unexpected `UnexpectedRollbackException`.

```java
// ❌ WRONG: Swallows exception, preventing TransactionInterceptor from knowing a failure occurred
@Transactional
public void processPayment(PaymentRequest req) {
    userAccountRepository.deduct(req.getAmount());
    try {
        gatewayClient.charge(req);
    } catch (GatewayException ex) {
        log.error("Payment failed", ex);
        // Exception swallowed! TransactionInterceptor will COMMIT the deduction!
    }
}
```

### The Fix
Either rethrow a runtime exception or manually mark the transaction for rollback:

```java
// ✅ Option 1: Rethrow as RuntimeException
throw new PaymentProcessingException("Gateway failed", ex);

// ✅ Option 2: Programmatically trigger rollback
TransactionAspectSupport.currentTransactionStatus().setRollbackOnly();
```

---

## 4. Failure Mode 4: Annotating `private` or `protected` Methods

### The Symptom
`@Transactional` on a `private` method is completely ignored by Spring.

### Root Cause
Spring AOP proxies use CGLIB subclassing or JDK dynamic proxies. Proxies can only override and intercept `public` methods. When Spring scans for `@Transactional`, it ignores non-public methods by default.

---

## 🧭 Navigation & Diagnostic Playbooks

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Hibernate N+1 & LazyInitializationException**](jpa-n-plus-one-and-lazy-init.md) | [**All Debugging Guides**](index.md) | [➡️ **Actuator Security & MDC Leaks**](actuator-security-and-logging-leaks.md) |

