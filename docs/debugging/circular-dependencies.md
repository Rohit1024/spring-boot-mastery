---
icon: lucide/refresh-cw
---

# Diagnosing circular dependencies in Spring Boot

One of the most common startup failures when designing services with constructor injection is the circular dependency exception.

---

## 1. The symptoms: `BeanCurrentlyInCreationException`

During application startup, the JVM terminates with a crash report:

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

## 2. Root cause mechanics

When both classes use constructor injection, Spring cannot instantiate either bean because each requires the other to already exist:

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
    Note over Ctx: 5. Deadlock. Neither instance exists yet.
    Ctx--xCtx: 6. Throws BeanCurrentlyInCreationException
```

---

## 3. Three resolution strategies

``` mermaid
flowchart TD
    Issue["Circular Dependency Detected (A <--> B)"]
    
    Issue --> S1["1. Extract Shared Logic into Service C<br/><b>(Architectural Best Practice)</b>"]
    Issue --> S2["2. Decouple via Spring Application Events<br/><b>(Event-Driven Architecture)</b>"]
    Issue --> S3["3. Break Cycle using @Lazy<br/><b>(Temporary Patch)</b>"]
```

---

### Strategy 1: Extract shared logic into a third service

In most cases, a circular dependency indicates poor separation of concerns where responsibilities are tangled.

``` mermaid
flowchart LR
    subgraph Before["Anti-pattern: Circular tangling"]
        A1[OrderService] <--> B1[PaymentService]
    end

    subgraph After["Clean design: Unidirectional flow"]
        A2[OrderService] --> N[NotificationService]
        B2[PaymentService] --> N
        A2 --> B2
    end
```

Extract the shared work (notification, validation, or receipt generation) into a dedicated service.

---

### Strategy 2: Decouple with Spring events

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
        // Update order status without referencing PaymentService directly.
    }
}
```

---

### Strategy 3: `@Lazy` annotation

If refactoring is not immediately practical, mark one of the constructor parameters with `@Lazy`. Spring injects a proxy placeholder instead of the eager instance, breaking the circular construction loop:

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

## 4. Diagnostic checklist

- [ ] Check if `spring.main.allow-circular-references=true` is enabled in `application.properties`. Avoid enabling this in production because it masks structural design flaws.
- [ ] Inspect the dependency graph to find which methods from Class A are called by Class B.
- [ ] Evaluate if an event via `ApplicationEventPublisher` or a dedicated coordinator service eliminates direct bidirectional references.

---

## Navigation and debugging index

| Previous | Debugging index | Next |
| :--- | :---: | ---: |
| First guide | [**All debugging guides**](index.md) | [**Troubleshooting REST API exceptions**](rest-validation-exception-debugging.md) |
