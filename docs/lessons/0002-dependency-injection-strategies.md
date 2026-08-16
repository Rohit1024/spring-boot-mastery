---
icon: lucide/git-merge
---

# 0002: Dependency Injection Strategies & Resolving Ambiguities

In [Lesson 0001](0001-spring-ioc-and-bean-lifecycle.md), we saw how the Spring IoC container instantiates and manages Beans. Now, we dive into **Dependency Injection (DI)**: the mechanism Spring uses to wire those beans together, the three injection flavors, and how to elegantly resolve injection collisions when multiple candidates exist.

---

## 1. The Three Injection Flavors: Architectural Comparison

Spring supports three ways to inject dependencies into a bean:

``` mermaid
flowchart TD
    subgraph Injection_Flavors["Dependency Injection Strategies"]
        C["1. Constructor Injection<br/><b>(Production Standard)</b>"]
        S["2. Setter Injection<br/><b>(Optional / Mutable Dependencies)</b>"]
        F["3. Field Injection<br/><b>(Anti-Pattern in Production)</b>"]
    end

    C --> C_Pros["Immutable (final fields)<br/>Fail-fast at compile/test time<br/>Zero reflection needed in Unit Tests"]
    S --> S_Pros["Allows reconfiguration at runtime<br/>Permits optional dependencies"]
    F --> F_Cons["Violates encapsulation<br/>Hides dependencies<br/>Requires reflection to test<br/>Masks circular dependencies"]
```

### Option 1: Constructor Injection (The Industry Standard)

```java
@Service
public class OrderService {

    // Dependencies are explicitly immutable
    private final PaymentGateway paymentGateway;
    private final NotificationClient notificationClient;

    // Single constructor: @Autowired is optional in modern Spring (4.3+)
    public OrderService(PaymentGateway paymentGateway, NotificationClient notificationClient) {
        this.paymentGateway = paymentGateway;
        this.notificationClient = notificationClient;
    }
}
```

!!! tip "Enterprise Pro-Tip: Clean Constructor Injection with Lombok"
    You can eliminate constructor boilerplate completely using Lombok's `@RequiredArgsConstructor`:
    ```java
    @Service
    @RequiredArgsConstructor
    public class OrderService {
        private final PaymentGateway paymentGateway;
        private final NotificationClient notificationClient;
    }
    ```

### Option 2: Setter Injection (Optional Dependencies)

```java
@Service
public class ReportService {

    private AuditLogger auditLogger;

    @Autowired(required = false)
    public void setAuditLogger(AuditLogger auditLogger) {
        this.auditLogger = auditLogger;
    }
}
```

### Option 3: Field Injection (Why It's an Anti-Pattern)

```java
@Service
public class UserService {
    @Autowired // Avoid doing this!
    private UserRepository userRepository;
}
```

!!! warning "Why Field Injection is Banned in Modern Enterprise Standards"
    1. **Hidden Dependencies**: You cannot tell what dependencies `UserService` needs by looking at its public constructor.
    2. **Immutability Broken**: Fields cannot be declared `final`.
    3. **Difficult Unit Testing**: To test `UserService` without booting the heavy Spring Context, you must use reflection or Mockito's `@InjectMocks` rather than simply passing a mock in `new UserService(mockRepo)`.

---

## 2. Resolving Ambiguity: `@Primary` vs `@Qualifier`

When an interface has multiple implementation beans in the `ApplicationContext`, Spring needs explicit instructions on which bean to inject.

``` mermaid
flowchart LR
    OS["OrderService"] -->|Needs| PG["«interface» PaymentGateway"]
    PG -.->|implements| S["StripeGateway<br/>@Qualifier(&quot;stripeGateway&quot;)"]
    PG -.->|implements| P["PayPalGateway<br/>@Primary"]
    PG -.->|implements| C["CryptoGateway<br/>@Qualifier(&quot;cryptoGateway&quot;)"]
```

### The Problem: `NoUniqueBeanDefinitionException`
If you attempt to inject `PaymentGateway` without disambiguation, Spring fails startup with:
`No qualifying bean of type 'PaymentGateway' available: expected single matching bean but found 3: stripeGateway, payPalGateway, cryptoGateway`.

---

### Solution A: Designate Default with `@Primary`

`@Primary` gives precedence to a specific bean when no qualifier is specified:

```java
@Component
@Primary
public class PayPalGateway implements PaymentGateway {
    @Override
    public void charge(BigDecimal amount) {
        // PayPal processing
    }
}
```

---

### Solution B: Exact Pinpointing with `@Qualifier`

Use `@Qualifier` to explicitly target a specific bean name at the injection site:

```java
@Service
public class OrderService {

    private final PaymentGateway stripeGateway;
    private final PaymentGateway defaultGateway;

    public OrderService(
            @Qualifier("stripeGateway") PaymentGateway stripeGateway,
            PaymentGateway defaultGateway) { // Injects PayPalGateway because of @Primary
        this.stripeGateway = stripeGateway;
        this.defaultGateway = defaultGateway;
    }
}
```

---

## 3. Advanced Pattern: Dynamic Strategy Collection Injection

Did you know Spring can inject **all beans** implementing an interface directly into a `List` or a `Map`? This allows you to build an open-closed **Strategy Pattern** without any factory boilerplate!

``` mermaid
sequenceDiagram
    autonumber
    actor Client as API Client
    participant Router as PaymentRouterService
    participant GatewayMap as PaymentGatewayMap
    participant Stripe as StripeGateway

    Client->>Router: processPayment("stripeGateway", $100)
    Router->>GatewayMap: get("stripeGateway")
    GatewayMap-->>Router: StripeGateway Instance
    Router->>Stripe: charge($100)
    Stripe-->>Client: Payment Confirmation
```

### Implementation Example:

```java
@Service
@RequiredArgsConstructor
public class PaymentRouterService {

    // Spring automatically populates this map with:
    // Key: Bean name (e.g. "stripeGateway", "payPalGateway")
    // Value: The corresponding PaymentGateway Bean instance
    private final Map<String, PaymentGateway> paymentGateways;

    public void routePayment(String provider, BigDecimal amount) {
        PaymentGateway gateway = paymentGateways.get(provider);
        if (gateway == null) {
            throw new IllegalArgumentException("Unsupported payment provider: " + provider);
        }
        gateway.charge(amount);
    }
}
```

---

## 4. Spring Bean Wiring Decision Tree

``` mermaid
flowchart TD
    Start(["Spring checks target dependency"]) --> TypeCheck{"How many beans match target type?"}
    TypeCheck -->|0 Candidates| ReqCheck{"Is @Autowired required=false?"}
    ReqCheck -->|Yes| SetNull["Inject null"]
    ReqCheck -->|No| FailNoBean["Throw NoSuchBeanDefinitionException"]
    
    TypeCheck -->|1 Candidate| InjectSingle["Inject single matching bean"]
    
    TypeCheck -->|Multiple Candidates| HasQualifier{"Is @Qualifier present at injection site?"}
    HasQualifier -->|Yes| MatchQualifier["Inject matching bean name"]
    HasQualifier -->|No| HasPrimary{"Is one bean marked @Primary?"}
    HasPrimary -->|Yes| MatchPrimary["Inject @Primary bean"]
    HasPrimary -->|No| FallbackName{"Does parameter/field name match a bean name?"}
    FallbackName -->|Yes| MatchName["Inject matching name bean"]
    FallbackName -->|No| FailAmbiguous["Throw NoUniqueBeanDefinitionException"]
```

---

## 5. Primary Source & Further Reading

- [Spring Framework Reference: Dependencies & Injection Mechanics](https://docs.spring.io/spring-framework/reference/core/beans/dependencies.html) — Official documentation on dependency resolution.
- Related Cheatsheet: [Spring Core & Annotations Cheatsheet](../cheatsheet/spring-core-annotations.md)

---

## 6. Knowledge Check & Retrieval Practice

??? question "Question 1: Why does constructor injection guarantee fail-fast behavior compared to field injection?"
    **Answer**: Constructor injection prevents creating an incomplete object, failing immediately during initial instantiation if any dependency is absent.

??? question "Question 2: If a class has both `@Primary` on one bean and `@Qualifier` at the injection point, which takes precedence?"
    **Answer**: The `@Qualifier` annotation takes absolute precedence, overriding `@Primary` to inject the explicitly requested bean name candidate.

??? question "Question 3: How does Spring resolve `Map<String, PluginService>` when multiple plugins implement `PluginService`?"
    **Answer**: Spring populates the map using bean names as keys and the respective initialized singleton bean instances as values.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0001: IoC Container & Lifecycle**](0001-spring-ioc-and-bean-lifecycle.md) | [**All Lessons**](index.md) | [**0003: Auto-Configuration & Starters** ➡️](0003-spring-boot-autoconfiguration-internals.md) |

💬 *Have questions on dependency wiring or strategy mapping? Ask anytime!*
