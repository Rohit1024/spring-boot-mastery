---
icon: lucide/refresh-cw
---

# Diagnosing Circular Dependencies in Spring Boot

One of the most common startup failures when designing services with constructor injection is the **Circular Dependency Exception**.

---

## 1. The Symptoms: `BeanCurrentlyInCreationException`

During application startup, the JVM terminates with a crash report similar to:

```text
***************************
APPLICATION FAILED TO START
***************************

Description:
The dependencies of some of the beans in the application context form a cycle:

┌─────┐
|  orderService (field private final com.example.PaymentService com.example.OrderService.paymentService)
↑     ↓
|  paymentService (field private final com.example.OrderService com.example.PaymentService.orderService)
└─────┘
```

---

## 2. Root Cause Mechanics

When both classes use strict **Constructor Injection**, Spring is caught in an impossible instantiation deadlock:

``` mermaid
sequenceDiagram
    autonumber
    participant Ctx as Spring ApplicationContext
    participant O as OrderService Constructor
    participant P as PaymentService Constructor

    Ctx->>O: 1. Needs to construct OrderService
    O->>Ctx: 2. Requests PaymentService instance
    Ctx->>P: 3. Needs to construct PaymentService
    P->>Ctx: 4. Requests OrderService instance
    Note over Ctx: 5. DEADLOCK! Neither instance exists yet!
    Ctx--xCtx: 6. Throws BeanCurrentlyInCreationException
```

---

## 3. The Three Resolution Strategies

``` mermaid
flowchart TD
    Issue["Circular Dependency Detected (A <--> B)"]
    
    Issue --> S1["1. Extract Shared Logic into Service C<br/><b>(Architectural Best Practice)</b>"]
    Issue --> S2["2. Decouple via Spring Application Events<br/><b>(Event-Driven Architecture)</b>"]
    Issue --> S3["3. Break Cycle using @Lazy<br/><b>(Temporary Patch)</b>"]
```

---

### Strategy 1: Extract Shared Logic into a Third Service (Recommended)

In 90% of cases, circular dependency indicates **poor separation of concerns** where responsibilities are tangled.

``` mermaid
flowchart LR
    subgraph Before["Anti-Pattern: Circular Tangling"]
        A1[OrderService] <--> B1[PaymentService]
    end

    subgraph After["Clean Design: Unidirectional Flow"]
        A2[OrderService] --> N[NotificationService]
        B2[PaymentService] --> N
        A2 --> B2
    end
```

**Refactoring Step**: Extract the shared functionality (e.g. notification, validation, receipt generation) into a dedicated service.

---

### Strategy 2: Decouple with Spring Events

Instead of `PaymentService` calling `OrderService.markCompleted()`, publish an application event:

```java
@Service
@RequiredArgsConstructor
public class PaymentService {

    private final ApplicationEventPublisher eventPublisher;

    public void processPayment(PaymentRequest request) {
        // Process payment...
        eventPublisher.publishEvent(new PaymentCompletedEvent(request.getOrderId()));
    }
}

@Service
public class OrderService {

    @EventListener
    public void onPaymentCompleted(PaymentCompletedEvent event) {
        // Update order status without directly referencing PaymentService
    }
}
```

---

### Strategy 3: `@Lazy` Annotation (Workaround)

If refactoring is not immediately feasible, mark one of the constructor parameters with `@Lazy`. Spring injects a lightweight proxy placeholder instead of the eager instance, breaking the circular construction loop:

```java
@Service
public class OrderService {

    private final PaymentService paymentService;

    public OrderService(@Lazy PaymentService paymentService) {
        this.paymentService = paymentService;
    }
}
```

---

## 4. Diagnostic Checklist

- [ ] Check if `spring.main.allow-circular-references=true` is enabled in `application.properties` (Avoid enabling this in production; it masks bad design).
- [ ] Inspect the dependency graph to find which methods from Class A are called by Class B.
- [ ] Evaluate if an event (`ApplicationEventPublisher`) or a dedicated coordinator service eliminates direct bidirectional references.

---

## 🧭 Navigation

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| *(First Guide)* | [**All Debugging Guides**](index.md) | [➡️ **Troubleshooting REST API Exceptions**](rest-validation-exception-debugging.md) |

