---
icon: lucide/bug
---

# Troubleshooting `@Transactional` failures, proxy bypasses, and silent rollback errors

Declarative transaction management in Spring Boot via `@Transactional` provides high-level convenience. Misunderstandings of AOP proxies, exception inheritance, and transaction propagation often result in transactions that fail to roll back or fail to begin altogether.

Here is a breakdown of the top 4 transaction failure modes, diagnostic flows, and concrete fixes.

---

## 1. Failure mode 1: The proxy self-invocation bypass

### Symptoms
Methods annotated with `@Transactional` execute database mutations, but when an exception occurs, no rollback is performed and no transaction boundary was created in SQL logs.

### Root cause
Calling a method on the `this` reference inside the same class calls the raw Java instance directly, bypassing Spring's CGLIB proxy wrapper (`TransactionInterceptor`).

``` mermaid
flowchart TD
    Client["Client Caller"] --> Proxy["OrderService CGLIB Proxy<br/><i>(TransactionInterceptor)</i>"]
    Proxy -->|"1. Invokes"| Outer["bulkProcessOrders()<br/><i>(NO @Transactional)</i>"]
    Outer -->|"2. this.processSingleOrder()<br/>Bypasses Proxy"| Inner["processSingleOrder()<br/><i>(@Transactional IGNORED)</i>"]
    Inner -->|"3. Throws RuntimeException"| DB["PostgreSQL<br/>Mutations NOT rolled back"]
```

### The fix
Extract the transactional logic into a separate dedicated `@Service` bean:

```java
@Service
public class OrderBatchProcessor {
    private final SingleOrderService singleOrderService;

    public void processAll(List<OrderRequest> requests) {
        for (var req : requests) {
            singleOrderService.processTransactional(req); // Passes through proxy.
        }
    }
}

@Service
public class SingleOrderService {
    @Transactional
    public void processTransactional(OrderRequest req) {
        // Correctly intercepted and wrapped in a transaction.
    }
}
```

---

## 2. Failure mode 2: Checked exceptions not triggering rollback

### Symptoms
A method throws a checked exception (`IOException`, `ParseException`, or a custom checked business exception), but the database still commits the partial data.

### Root cause
By default, Spring's `RuleBasedTransactionAttribute` only rolls back on unchecked exceptions (`RuntimeException` and `Error`).

``` mermaid
sequenceDiagram
    autonumber
    participant App as Service Method
    participant Interceptor as TransactionInterceptor
    participant DB as PostgreSQL

    App->>DB: INSERT INTO users ...
    App-->>Interceptor: throws CustomCheckedException (extends Exception)
    Note over Interceptor: Is exception an instance of RuntimeException?<br/>NO. It is a checked Exception.
    Interceptor->>DB: COMMIT (Partial Data Persisted)
```

### The fix
Declare `rollbackFor = Exception.class` on transactional business methods:

```java
@Transactional(rollbackFor = Exception.class)
public void processFinancialSettlement(Long batchId) throws SettlementCheckedException {
    // Both checked and unchecked exceptions will now trigger rollback.
}
```

---

## 3. Failure mode 3: Swallowed exceptions in `try-catch`

### Symptoms
An exception occurs inside a helper call, you catch and log it, but the transaction still commits or throws an unexpected `UnexpectedRollbackException`.

```java
// Swallows exception, preventing TransactionInterceptor from knowing a failure occurred
@Transactional
public void processPayment(PaymentRequest req) {
    userAccountRepository.deduct(req.getAmount());
    try {
        gatewayClient.charge(req);
    } catch (GatewayException ex) {
        log.error("Payment failed", ex);
        // Exception swallowed. TransactionInterceptor will COMMIT the deduction.
    }
}
```

### The fix
Either rethrow a runtime exception or manually mark the transaction for rollback:

```java
// Option 1: Rethrow as RuntimeException
throw new PaymentProcessingException("Gateway failed", ex);

// Option 2: Programmatically trigger rollback
TransactionAspectSupport.currentTransactionStatus().setRollbackOnly();
```

---

## 4. Failure mode 4: Annotating `private` or `protected` methods

### Symptoms
`@Transactional` on a `private` method is ignored by Spring.

### Root cause
Spring AOP proxies use CGLIB subclassing or JDK dynamic proxies. Proxies can only override and intercept `public` methods. When Spring scans for `@Transactional`, it ignores non-public methods by default.

---

## Navigation and debugging index

| Previous | Debugging index | Next |
| :--- | :---: | ---: |
| [**Hibernate N+1 and LazyInitializationException**](jpa-n-plus-one-and-lazy-init.md) | [**All debugging guides**](index.md) | [**Actuator security and MDC leaks**](actuator-security-and-logging-leaks.md) |
