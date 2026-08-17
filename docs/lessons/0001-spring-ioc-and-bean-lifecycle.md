---
icon: lucide/box
---

# 0001: Spring IoC Container, Bean Scopes & Lifecycle

Welcome to your first lesson in mastering the Spring Framework. In this lesson, we demystify the beating heart of Spring: the **Inversion of Control (IoC) Container**, how **Spring Beans** are instantiated and managed, and the precise **Bean Lifecycle** phases.

---

## 1. Why IoC Container? (The Problem It Solves)

In standard Object-Oriented programming, if Class `OrderService` needs `PaymentGateway` and `NotificationService`, it creates them directly using `new`:

```java
// Tightly Coupled (Anti-Pattern in Enterprise Apps)
public class OrderService {
    private PaymentGateway paymentGateway = new StripePaymentGateway();
    private NotificationService notificationService = new EmailNotificationService();
}
```

### The Problems:
1. **Tight Coupling**: You cannot easily swap `StripePaymentGateway` with `MockPaymentGateway` during testing.
2. **Scattered Configuration**: Every class decides how to construct its own dependencies, leading to duplicate configuration and unmanaged resource lifecycles.

### The Solution: Inversion of Control (IoC)
With IoC, **you do not create objects; the Container creates and injects them.** Control over the object lifecycle is inverted from your application code to the framework.

``` mermaid
flowchart TD
    A[Java Classes / Components] --> C[Spring IoC Container]
    B[Configuration Metadata<br/>@Configuration / @Component] --> C
    C --> D[Fully Configured Ready-to-Use Application]
```

---

## 2. Spring IoC Containers: `BeanFactory` vs `ApplicationContext`

Spring provides two container interfaces:

| Container Interface | Loading Strategy | Enterprise Features (AOP, Events, i18n) | Recommended Use |
| :--- | :--- | :--- | :--- |
| **`BeanFactory`** | Lazy (loads beans on `getBean()`) | Basic DI only | Resource-constrained legacy devices |
| **`ApplicationContext`** | Eager (loads singletons at startup) | Full enterprise suite (AOP, Events, Env, Web) | **Always use in modern Spring Boot apps** |

Common `ApplicationContext` implementations include `AnnotationConfigApplicationContext` and `AnnotationConfigServletWebServerApplicationContext` (used by Spring Boot Web).

---

## 3. Registering Spring Beans

A **Spring Bean** is simply a Java object instantiated, assembled, and managed by the Spring IoC container.

You can declare beans in two primary ways:

### Option A: Stereotype Annotations (Component Scanning)
Mark classes with `@Component` (or specialized stereotypes: `@Service`, `@Repository`, `@Controller`):

```java
@Service
public class OrderService {
    private final PaymentGateway paymentGateway;

    // Constructor Injection (Best Practice)
    public OrderService(PaymentGateway paymentGateway) {
        this.paymentGateway = paymentGateway;
    }
}
```

### Option B: Java Configuration Class (`@Configuration` + `@Bean`)
Best when configuring third-party libraries where you cannot edit source code:

```java
@Configuration
public class ThirdPartyConfig {

    @Bean
    public ObjectMapper objectMapper() {
        return new ObjectMapper()
                .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false);
    }
}
```

---

## 4. Bean Scopes

Bean scope determines how many instances of a bean are created and when:

``` mermaid
stateDiagram-v2
    [*] --> Singleton: Default (1 instance per ApplicationContext)
    [*] --> Prototype: New instance on every getBean() or injection
    [*] --> Request: 1 instance per HTTP Request (Web only)
    [*] --> Session: 1 instance per HTTP Session (Web only)
```

!!! tip "Production Rule of Thumb"
    99% of your Spring services, repositories, and controllers should be **Singletons**. Make sure singletons are **stateless** (thread-safe) because multiple threads will execute methods on the same shared instance concurrently.

---

## 5. The Complete Spring Bean Lifecycle

Understanding the lifecycle sequence is critical for initializing database connections, background workers, or teardown tasks.

``` mermaid
sequenceDiagram
    autonumber
    participant C as IoC Container
    participant B as Bean Instance
    participant P as BeanPostProcessors

    C->>B: 1. Instantiation (calls constructor)
    C->>B: 2. Populate Properties (Dependency Injection)
    C->>B: 3. BeanNameAware / ApplicationContextAware
    C->>P: 4. postProcessBeforeInitialization()
    C->>B: 5. @PostConstruct Method
    C->>B: 6. InitializingBean.afterPropertiesSet()
    C->>B: 7. Custom initMethod
    C->>P: 8. postProcessAfterInitialization() (Generates AOP Proxies here!)
    Note over B: Bean is LIVE & READY in Context
    C->>B: 9. @PreDestroy Method
    C->>B: 10. DisposableBean.destroy()
    C->>B: 11. Custom destroyMethod
```

### Lifecycle Hook Code Example

```java
package com.example.service;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class CacheWarmupService {

    private static final Logger log = LoggerFactory.getLogger(CacheWarmupService.class);

    public CacheWarmupService() {
        log.info("Phase 1: Constructor called (Instantiation)");
    }

    @PostConstruct
    public void init() {
        log.info("Phase 5: @PostConstruct executed - Warming up local cache...");
    }

    @PreDestroy
    public void cleanup() {
        log.info("Phase 9: @PreDestroy executed - Flushing buffers before shutdown...");
    }
}
```

!!! note "AOP Proxy Creation Note"
    Notice **Step 8 (`postProcessAfterInitialization`)** in the diagram above. This is where Spring wraps your raw bean in dynamic proxies (CGLIB or JDK Dynamic Proxies) to enable `@Transactional`, `@Async`, and `@Cacheable`.

---

## 6. Spring Boot 3 vs Spring Boot 4: IoC & Bean Lifecycle Evolution

As the Spring ecosystem advances from Spring Boot 3.x (Spring Framework 6) to **Spring Boot 4.x (Spring Framework 7)**, the core IoC container undergoes major architectural upgrades:

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Spring 6)"]
        J17["Java 17 Baseline"]
        Reflect["Runtime Reflection & CGLIB"]
        CustomNull["org.springframework.lang.@Nullable"]
        ManualAOT["Opt-in AOT Hints"]
    end

    subgraph SB4["Spring Boot 4.x (Spring 7)"]
        J21["Java 21/25 Baseline (Loom Native)"]
        ClassFileAPI["Class-File API & Direct Invocations"]
        JSpecify["Standard JSpecify Null-Safety"]
        NativeFirst["Native-First AOT Compilation"]
    end

    SB3 ==>|Generational Evolution| SB4
```

### Key Differences & Configuration Comparison

| Architectural Capability | Spring Boot 3.x (Spring Framework 6) | Spring Boot 4.x (Spring Framework 7) |
| :--- | :--- | :--- |
| **Java Baseline** | Java 17 (Supports Java 21) | **Java 21 LTS / Java 25 LTS Baseline** |
| **Null-Safety Standard** | Custom `@NonNull` / `@Nullable` annotations. | **Standard JSpecify (`org.jspecify.annotations.*`)** across container APIs. |
| **AOT & GraalVM Engine** | Required manual `@RegisterReflectionForBinding` runtime hints for dynamic beans. | **Native-First AOT**: Container generates static factory registrations at build time automatically. |
| **Virtual Threads (Loom)** | Opt-in via `spring.threads.virtual.enabled=true`. | **Virtual Threads Enabled by Default** with thread-safe singleton synchronization. |
| **Bytecode Manipulation** | Heavy reliance on bundled CGLIB / ByteBuddy proxies. | **JDK 24+ Class-File API** for zero-dependency proxy generation and lifecycle interceptors. |

```java
// Spring Boot 4.x / Spring 7: Standard JSpecify Null-Safety in Bean Declarations
import org.jspecify.annotations.NonNull;
import org.jspecify.annotations.Nullable;
import org.springframework.stereotype.Service;

@Service
public class PaymentProcessingService {

    private final PaymentGateway gateway;
    private final @Nullable AuditLogger auditLogger; // Explicitly marked optional for DI

    public PaymentProcessingService(PaymentGateway gateway, @Nullable AuditLogger auditLogger) {
        this.gateway = gateway;
        this.auditLogger = auditLogger;
    }
}
```

---

## 7. Primary Source & Further Reading

- [Spring Core Technologies: The IoC Container](https://docs.spring.io/spring-framework/reference/core/beans.html) — Read Section 1.1 to 1.6 for official architecture specifications.
- [Spring Framework 7 / Boot 4 Roadmap](https://github.com/spring-projects/spring-framework/wiki) — Ahead-of-time engine, JSpecify adoption, and Java 21+ baselines.
- Related Cheatsheet: [Spring Core & Annotations Cheatsheet](../cheatsheet/spring-core-annotations.md)

---

## 8. Knowledge Check & Retrieval Practice

Test your understanding of the concepts covered in this lesson.

??? question "Question 1: Why does Spring default to Singleton scope for Beans, and what threading requirement does this impose?"
    **Answer**: Singleton scope minimizes memory footprint and object creation overhead across requests. Because the single instance is shared across all concurrent web request threads, the bean **must be stateless** (i.e. cannot store per-request mutable state in instance variables).

??? question "Question 2: At which phase of the Spring Bean lifecycle are `@Transactional` and AOP proxies generated?"
    **Answer**: In the `BeanPostProcessor.postProcessAfterInitialization()` phase, after the bean has been instantiated, properties injected, and `@PostConstruct` executed.

??? question "Question 3: When should you use `@Configuration + @Bean` instead of `@Component`?"
    **Answer**: Use `@Configuration + @Bean` when you need to configure and instantiate classes from third-party libraries whose source code cannot be annotated, or when bean creation requires complex programmatic setup.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| *(Start of Curriculum)* | [**All Lessons**](index.md) | [**0002: Dependency Injection Strategies** ➡️](0002-dependency-injection-strategies.md) |

💬 *Have questions on IoC, Bean scopes, or lifecycle hooks? Ask anytime!*
