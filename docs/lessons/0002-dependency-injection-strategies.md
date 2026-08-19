---
icon: lucide/git-merge
---

# 0002: Dependency injection strategies and resolving ambiguities

Dependency injection is how Spring wires beans together. This lesson covers constructor, setter, and field injection, along with techniques to resolve bean naming collisions when multiple candidates match.

---

## 1. The three injection flavors: Architectural comparison

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

### Option 1: Constructor injection (the industry standard)

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

### Option 2: Setter injection (optional dependencies)

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

### Option 3: Field injection (why its an anti-pattern)

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

## 2. Resolving ambiguity: `@Primary` vs `@Qualifier`

When an interface has multiple implementation beans in the `ApplicationContext`, Spring needs explicit instructions on which bean to inject.

``` mermaid
flowchart TD
    OS["OrderService"] -->|Needs| PG["«interface» PaymentGateway"]
    PG -.->|implements| S["StripeGateway<br/>@Qualifier(&quot;stripeGateway&quot;)"]
    PG -.->|implements| P["PayPalGateway<br/>@Primary"]
    PG -.->|implements| C["CryptoGateway<br/>@Qualifier(&quot;cryptoGateway&quot;)"]
```

### The problem: `NoUniqueBeanDefinitionException`
If you attempt to inject `PaymentGateway` without disambiguation, Spring fails startup with:
`No qualifying bean of type 'PaymentGateway' available: expected single matching bean but found 3: stripeGateway, payPalGateway, cryptoGateway`.

---

### Solution a: Designate default with `@Primary`

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

### Solution b: Exact pinpointing with `@Qualifier`

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

## 3. Advanced pattern: Dynamic strategy collection injection

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

### Implementation example

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

## 4. Spring bean wiring decision tree

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

## 5. Spring Boot 3 vs Spring Boot 4: Dependency injection evolution

The DI container evolves significantly in **Spring Boot 4 / Spring Framework 7**:

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Spring 6)"]
        ClassDI["Standard Class Constructor DI"]
        SpringLang["org.springframework.lang.@Nullable"]
        TLInject["ThreadLocal Request/Session Injections"]
    end

    subgraph SB4["Spring Boot 4.x (Spring 7)"]
        RecordDI["Java Record Beans as First-Class Components"]
        JSpecifyDI["Standard JSpecify Null-Safety Enforcement"]
        ScopedValDI["Java 21+ ScopedValue Context Injection"]
    end

    SB3 ==>|Modernization| SB4
```

### Key differences and configuration comparison

| Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Record Components as Beans** | Supported, but required manual component annotations or configuration classes. | **First-Class Component Records**: Clean immutable record beans with canonical constructor DI. |
| **Optional Dependency Null-Safety** | `@Autowired(required = false)` or `Optional<T>` wrapping. | **JSpecify `@Nullable` Parameter Type**: Enforces compile-time and container-level null-safety. |
| **Thread Context Propagation** | Backed by `ThreadLocal` proxies (heavy footprint under Loom). | **`ScopedValue` Context Injection**: High-performance, immutable context sharing across Virtual Threads. |

```java
// Spring Boot 4 / Spring 7: Immutable Record Bean with JSpecify Constructor DI
package com.example.service;

import org.jspecify.annotations.NonNull;
import org.jspecify.annotations.Nullable;
import org.springframework.stereotype.Service;

@Service
public record OrderProcessingService(
    @NonNull PaymentGateway paymentGateway,
    @NonNull InventoryClient inventoryClient,
    @Nullable FraudDetector fraudDetector // Optional: injected as null without throwing NoSuchBeanDefinitionException
) {
    public void processOrder(Long orderId) {
        if (fraudDetector != null) {
            fraudDetector.verify(orderId);
        }
        paymentGateway.charge(orderId);
        inventoryClient.reserve(orderId);
    }
}
```

---

## 6. Primary sources and further reading

- [Spring Framework Reference: Dependencies & Injection Mechanics](https://docs.spring.io/spring-framework/reference/core/beans/dependencies.html), Official documentation on dependency resolution.
- Related Cheatsheet: [Spring Core & Annotations Cheatsheet](../cheatsheet/spring-core-annotations.md)

---

## 7. Knowledge check and practice

??? question "Question 1: Why does constructor injection guarantee fail-fast behavior compared to field injection?"
    **Answer**: Constructor injection prevents creating an incomplete object, failing immediately during initial instantiation if any dependency is absent.

??? question "Question 2: If a class has both `@Primary` on one bean and `@Qualifier` at the injection point, which takes precedence?"
    **Answer**: The `@Qualifier` annotation takes absolute precedence, overriding `@Primary` to inject the explicitly requested bean name candidate.

??? question "Question 3: How does Spring resolve `Map<String, PluginService>` when multiple plugins implement `PluginService`?"
    **Answer**: Spring populates the map using bean names as keys and the respective initialized singleton bean instances as values.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0001: IoC Container & Lifecycle**](0001-spring-ioc-and-bean-lifecycle.md) | [**All Lessons**](index.md) | [**0003: Auto-Configuration & Starters**](0003-spring-boot-autoconfiguration-internals.md) |

