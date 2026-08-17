---
icon: lucide/cpu
---

# 0011: Design Patterns in Spring: Strategy & Decorator Patterns

Enterprise architectures thrive on **clean separation of concerns** and the **Open/Closed Principle (OCP)** — systems should be open for extension but closed for modification.

In this lesson, we explore how Spring's **Inversion of Control (IoC) Container** natively supercharges classic Gang of Four (GoF) design patterns, focusing on the **Strategy Pattern** (eliminating `if/else` ladders) and the **Decorator Pattern** (modular behavior composition).

---

## 1. The Strategy Pattern in Spring Boot

### The Problem: Rigid `switch` Statements & `if/else` Sprawl

```java
// ❌ ANTI-PATTERN: Violates Open/Closed Principle (OCP)
public void processPayment(String gatewayType, BigDecimal amount) {
    if ("STRIPE".equalsIgnoreCase(gatewayType)) {
        stripeClient.charge(amount);
    } else if ("PAYPAL".equalsIgnoreCase(gatewayType)) {
        paypalClient.pay(amount);
    } else if ("CRYPTO".equalsIgnoreCase(gatewayType)) {
        cryptoClient.transfer(amount);
    } else {
        throw new IllegalArgumentException("Unsupported gateway: " + gatewayType);
    }
}
```
*Every time your company adds a new payment provider, you are forced to modify, re-test, and redeploy the core payment orchestration class.*

---

### The Spring Solution: Automatic Strategy Map Injection

Spring's IoC container can automatically inject all implementations of an interface into a `Map<String, PaymentStrategy>` or `List<PaymentStrategy>`, keyed by the Spring Bean name:

``` mermaid
flowchart TD
    Client["📱 Client Request<br/><code>POST /checkout?gateway=stripe</code>"] --> Dispatcher["⚡ PaymentContextService<br/><i>(Injects Map&lt;String, PaymentStrategy&gt;)</i>"]
    
    subgraph SpringRegistry["Spring IoC Managed Strategy Registry"]
        Dispatcher -->|lookup 'stripe'| S1["StripePaymentStrategy<br/><i>(@Component('stripe'))</i>"]
        Dispatcher -.->|lookup 'paypal'| S2["PaypalPaymentStrategy<br/><i>(@Component('paypal'))</i>"]
        Dispatcher -.->|lookup 'crypto'| S3["CryptoPaymentStrategy<br/><i>(@Component('crypto'))</i>"]
    end
    
    S1 --> Gateways["💳 Stripe API Gateway"]
```

---

### Strategy Pattern Code Implementation

#### Step 1: Define the Common Strategy Interface
```java
package com.example.demo.strategy;

import java.math.BigDecimal;

public interface PaymentStrategy {
    String getProviderName(); // e.g. "stripe", "paypal"
    PaymentResult executePayment(String customerId, BigDecimal amount);
}
```

#### Step 2: Implement Strategy Beans
```java
package com.example.demo.strategy;

import org.springframework.stereotype.Component;
import java.math.BigDecimal;

@Component("stripe")
public class StripePaymentStrategy implements PaymentStrategy {
    @Override
    public String getProviderName() {
        return "stripe";
    }

    @Override
    public PaymentResult executePayment(String customerId, BigDecimal amount) {
        // Stripe SDK logic
        return new PaymentResult(true, "STRIPE-TX-9912");
    }
}

@Component("paypal")
public class PaypalPaymentStrategy implements PaymentStrategy {
    @Override
    public String getProviderName() {
        return "paypal";
    }

    @Override
    public PaymentResult executePayment(String customerId, BigDecimal amount) {
        // PayPal SDK logic
        return new PaymentResult(true, "PAYPAL-TX-4401");
    }
}
```

#### Step 3: Implement the Context Service with Map Injection
```java
package com.example.demo.service;

import com.example.demo.strategy.PaymentResult;
import com.example.demo.strategy.PaymentStrategy;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.Map;
import java.util.Optional;

@Service
public class PaymentContextService {

    // Spring automatically populates this map with all PaymentStrategy beans!
    // Key = Bean Name ("stripe", "paypal"), Value = Strategy instance
    private final Map<String, PaymentStrategy> paymentStrategies;

    public PaymentContextService(Map<String, PaymentStrategy> paymentStrategies) {
        this.paymentStrategies = paymentStrategies;
    }

    public PaymentResult processPayment(String gatewayKey, String customerId, BigDecimal amount) {
        PaymentStrategy strategy = Optional.ofNullable(paymentStrategies.get(gatewayKey.toLowerCase()))
                .orElseThrow(() -> new IllegalArgumentException("Unsupported payment provider: " + gatewayKey));

        return strategy.executePayment(customerId, amount);
    }
}
```
!!! tip "Zero-Touch Extension"
    To add Apple Pay, simply create `@Component("applepay") public class ApplePayStrategy implements PaymentStrategy`. The `PaymentContextService` requires **zero code changes**!

---

## 2. The Decorator / Wrapper Pattern in Spring

The **Decorator Pattern** allows behavior to be added to an individual object dynamically without affecting other instances or altering the base class.

``` mermaid
flowchart TD
    Client["🎮 OrderController"] --> Dec["🛡️ CachedOrderServiceDecorator<br/><i>(@Primary - Checks Redis Cache)</i>"]
    Dec -->|Cache Miss| Core["⚙️ DefaultOrderService<br/><i>(Executes heavy DB queries)</i>"]
```

### Implementing a Decorator with `@Primary` and Delegation

#### Step 1: Base Interface
```java
package com.example.demo.service;

import com.example.demo.dto.OrderDetails;

public interface OrderService {
    OrderDetails getOrderDetails(Long orderId);
}
```

#### Step 2: Core Concrete Service
```java
package com.example.demo.service;

import org.springframework.stereotype.Service;

@Service("defaultOrderService")
public class DefaultOrderService implements OrderService {
    @Override
    public OrderDetails getOrderDetails(Long orderId) {
        // Simulates heavy database queries with multiple JOINs
        return new OrderDetails(orderId, "COMPLETED", 150.00);
    }
}
```

#### Step 3: Decorator with Caching and Logging
```java
package com.example.demo.service;

import com.example.demo.dto.OrderDetails;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Primary;
import org.springframework.stereotype.Service;

@Service
@Primary // Injected by default into all controllers requesting OrderService
public class CachedOrderServiceDecorator implements OrderService {

    private static final Logger log = LoggerFactory.getLogger(CachedOrderServiceDecorator.class);
    private final OrderService delegate;

    public CachedOrderServiceDecorator(@Qualifier("defaultOrderService") OrderService delegate) {
        this.delegate = delegate;
    }

    @Override
    public OrderDetails getOrderDetails(Long orderId) {
        log.info("🔍 Decorator: Checking Redis cache for order ID: {}", orderId);
        
        // Cache lookup logic here...
        // If cache miss, delegate to the core service:
        OrderDetails details = delegate.getOrderDetails(orderId);
        
        log.info("💾 Decorator: Populated Redis cache for order ID: {}", orderId);
        return details;
    }
}
```

---

## 3. Other Core Spring Design Patterns Summary

| GoF Design Pattern | Spring Framework Implementation |
| :--- | :--- |
| **Front Controller** | `DispatcherServlet` routing all HTTP traffic through a single entry point. |
| **Template Method** | `JdbcTemplate`, `TransactionTemplate`, `RestTemplate`, `JmsTemplate`. |
| **Proxy Pattern** | Spring AOP, `@Transactional`, `@Async`, `@Cacheable` dynamic proxies. |
| **Observer Pattern** | Spring Event Publication (`ApplicationEventPublisher` and `@EventListener`). |
| **Factory Pattern** | `BeanFactory`, `FactoryBean<T>`, `ApplicationContext`. |

---

## 4. Spring Boot 3 vs Spring Boot 4: Design Pattern Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        MapStrategy["Map<String, Strategy> IoC Map Injection"]
        DecoratorProxies["Manual Decorator Classes / AOP CGLIB"]
        OpenHierarchy["Open Interface Hierarchies"]
    end

    subgraph SB4["Spring Boot 4.x"]
        SealedStrategy["Java 21+ Sealed Interfaces & Exhaustive Switch"]
        FunctionalBeans["Functional Bean Registration for Dynamic Strategies"]
        ClassFileDecorator["Class-File API Clean Decorators"]
    end

    SB3 ==>|Language Feature Convergence| SB4
```

### Key Differences & Configuration Comparison

| Pattern Implementation | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Strategy Pattern** | Relied primarily on Spring IoC `Map<String, T>` autowiring and string keys. | **Sealed Interface Hierarchies + Pattern Matching**: Exhaustive, type-safe compile-time strategy selection. |
| **Decorator Pattern** | `@Primary` wrapper beans or CGLIB AOP dynamic proxies. | **Virtual Thread-Friendly Decorators**: Zero-proxy ScopedValue and functional decorators. |
| **Factory Pattern** | Heavy use of `FactoryBean<T>` with reflection. | **Declarative Factory Methods**: Native AOT compiled functional bean registrations. |

```java
// Spring Boot 4 / Java 21+ Type-Safe Strategy Dispatch using Sealed Interfaces
public sealed interface PaymentMethod permits CreditCard, PayPal, Crypto {}

public record CreditCard(String cardNumber) implements PaymentMethod {}
public record PayPal(String email) implements PaymentMethod {}
public record Crypto(String walletAddress) implements PaymentMethod {}

@Service
public class ModernPaymentProcessor {

    public String process(PaymentMethod method, BigDecimal amount) {
        // Compiler guarantees exhaustiveness - no default case or map lookup needed!
        return switch (method) {
            case CreditCard cc -> "Charged CC: " + cc.cardNumber();
            case PayPal pp     -> "Charged PayPal: " + pp.email();
            case Crypto c      -> "Transferred Crypto to: " + c.walletAddress();
        };
    }
}
```

---

## 5. Primary Sources & Further Reading

- [Design Patterns: Elements of Reusable Object-Oriented Software (Gang of Four)](https://en.wikipedia.org/wiki/Design_Patterns) — Foundational design pattern principles.
- [Spring Framework IoC: Collection & Map Injection](https://docs.spring.io/spring-framework/reference/core/beans/annotation-config/autowired.html) — Spring's automatic map and list autowiring mechanics.
- [Java 21 Pattern Matching for switch](https://docs.oracle.com/en/java/javase/21/language/pattern-matching-switch.html) — Official documentation for pattern matching in switch.

---

## 6. Knowledge Check & Retrieval Practice

??? question "Question 1: How does Spring's IoC container resolve `public PaymentService(Map<String, PaymentStrategy> map)`?"
    **Answer**: Spring automatically locates all beans implementing `PaymentStrategy` in the `ApplicationContext` and puts them in the map where the key is the Spring bean name and the value is the bean instance.

??? question "Question 2: How does the Strategy pattern uphold the Open/Closed Principle (OCP)?"
    **Answer**: New strategies can be introduced simply by authoring a new `@Component` implementing the interface without modifying or recompiling existing dispatching classes.

??? question "Question 3: How does the `@Primary` annotation facilitate the Decorator pattern in Spring?"
    **Answer**: `@Primary` ensures that when other components (like controllers) autowire the interface, Spring supplies the decorator wrapper rather than the un-decorated underlying service.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0010: Standardizing Response Envelopes & DTO Pattern**](0010-dto-pattern-and-response-envelopes.md) | [**All Lessons**](index.md) | [➡️ **0012: JDBC vs Hibernate ORM Internals**](0012-jdbc-vs-hibernate-orm-internals.md) |

🎉 **Congratulations on completing Module 2: RESTful Web Services & Spring MVC!**

