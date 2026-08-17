---
icon: lucide/layers
---

# 0005: Spring Profiles & Multi-Environment Configuration

Enterprise applications must run seamlessly across multiple deployment stages: **local developer machines (`dev`), integration environments (`stage`), and live clusters (`prod`)**.

In this lesson, we explore **Spring Profiles**, configuration loading precedence, type-safe **`@ConfigurationProperties`**, and how to activate profile-specific beans cleanly.

---

## 1. Why Profiles Matter

A single hard-coded configuration cannot serve all environments:

``` mermaid
flowchart TD
    subgraph Env_Dev["Developer Laptop ('dev')"]
        D1["H2 In-Memory DB"]
        D2["Mock Email Client"]
        D3["Console Debug Logs"]
    end

    subgraph Env_Stage["Staging Cluster ('stage')"]
        S1["PostgreSQL QA Instance"]
        S2["Mailtrap Sandbox"]
        S3["Standard Info Logs"]
    end

    subgraph Env_Prod["Production AWS ('prod')"]
        P1["PostgreSQL Aurora Cluster"]
        P2["AWS SES Real Email"]
        P3["JSON Logstash Logs"]
    end

    Env_Dev ~~~ Env_Stage ~~~ Env_Prod
```

---

## 2. Configuration File Structure

Spring Boot automatically searches for profile-specific configuration files following the naming convention:
`application-{profile}.properties` (or `.yml`).

### Directory Layout
```text
src/main/resources/
├── application.yml         # Shared base defaults across all environments
├── application-dev.yml     # Local overrides (dev profile)
├── application-stage.yml   # Staging overrides (stage profile)
└── application-prod.yml    # Production overrides (prod profile)
```

### Multi-Document YAML Format (Clean Alternative)
You can combine all profiles into a single `application.yml` file using document separators (`---`):

```yaml
spring:
  application:
    name: order-service
server:
  port: 8080

---
# Dev Profile
spring:
  config:
    activate:
      on-profile: dev
  datasource:
    url: jdbc:h2:mem:orderdb
logging:
  level:
    com.example: DEBUG

---
# Prod Profile
spring:
  config:
    activate:
      on-profile: prod
  datasource:
    url: jdbc:postgresql://aurora-cluster.prod:5432/orderdb
server:
  port: 8443
logging:
  level:
    root: WARN
```

---

## 3. Activating Profiles in Different Environments

Spring Boot gives you multiple ways to activate profiles depending on where your code runs:

| Method | Syntax | Standard Usage |
| :--- | :--- | :--- |
| **Environment Variable** | `SPRING_PROFILES_ACTIVE=prod` | **Standard in Docker & Kubernetes** |
| **CLI Argument** | `java -jar app.jar --spring.profiles.active=prod` | Traditional VM / Systemd service |
| **JVM System Property** | `java -Dspring.profiles.active=stage -jar app.jar` | CI/CD build scripts |
| **Default in Config** | `spring.profiles.default=dev` | Local developer fallback when none set |

---

## 4. Property Resolution Order (Precedence)

When a property is defined in multiple places, Spring Boot resolves them using a strict precedence order (higher overwrites lower):

``` mermaid
flowchart TD
    CLI["1. Command-line arguments (--server.port=9090)"] --> ENV["2. OS Environment Variables (SERVER_PORT=9090)"]
    ENV --> PROF["3. Profile-specific files (application-prod.yml)"]
    PROF --> BASE["4. Base application file (application.yml)"]
    BASE --> DEF["5. Default values in @Value / @ConfigurationProperties"]
```

---

## 5. Profile-Specific Bean Registration with `@Profile`

You can conditionally register beans based on active profiles:

``` mermaid
flowchart TD
    Context["Spring ApplicationContext"]
    
    Context --> ProfileCheck{"Active Profile?"}
    ProfileCheck -->|dev or test| Mock["MockNotificationService<br/><i>(Logs email to console)</i>"]
    ProfileCheck -->|prod| SES["AwsSesNotificationService<br/><i>(Sends real email via AWS SES)</i>"]
```

### Code Example:

```java
public interface NotificationService {
    void sendNotification(String to, String message);
}

// Active ONLY in 'dev' or 'test' environments
@Service
@Profile({"dev", "test"})
public class MockNotificationService implements NotificationService {
    private static final Logger log = LoggerFactory.getLogger(MockNotificationService.class);

    @Override
    public void sendNotification(String to, String message) {
        log.info("[MOCK EMAIL] Sending to {}: {}", to, message);
    }
}

// Active in 'prod' environment
@Service
@Profile("prod")
public class AwsSesNotificationService implements NotificationService {
    @Override
    public void sendNotification(String to, String message) {
        // Calls real AWS SES API
    }
}
```

!!! tip "Negated Profiles"
    You can use `@Profile("!prod")` to activate a bean in every environment *except* production.

---

## 6. Type-Safe Configuration with `@ConfigurationProperties`

Instead of scattering `@Value` annotations across your codebase, use type-safe configuration classes:

### The Configuration Class:
```java
@Configuration
@ConfigurationProperties(prefix = "app.payment")
@Validated // Enforces Bean Validation at startup!
@Getter
@Setter
public class PaymentGatewayProperties {

    @NotBlank
    private String apiKey;

    @Min(1000)
    private int timeoutMillis = 5000;

    private boolean sandboxMode;
}
```

### The Matching YAML:
```yaml
app:
  payment:
    api-key: "prod_live_sec_99341"
    timeout-millis: 3000
    sandbox-mode: false
```

---

## 7. Spring Boot 3 vs Spring Boot 4: Configuration & Environment Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        ClassProps["POJO @ConfigurationProperties with Getters/Setters"]
        K8sPolling["External Spring Cloud Kubernetes Polling"]
        ManualImport["spring.config.import syntax"]
    end

    subgraph SB4["Spring Boot 4.x"]
        RecordProps["Record @ConfigurationProperties (Immutable Default)"]
        NativeK8sReload["Built-In Kubernetes Volume Watch & Hot-Reload"]
        ValidatedRecords["Jakarta Validation 3.1 on Record Fields"]
    end

    SB3 ==>|Cloud-Native Streamlining| SB4
```

### Key Differences & Configuration Comparison

| Configuration Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **`@ConfigurationProperties`** | Typically mutable POJOs or constructor-bound records requiring `@ConstructorBinding`. | **Immutable Java Records by Default**: Fully integrated without requiring `@ConstructorBinding`. |
| **Kubernetes ConfigMap Live Reload** | Required `spring-cloud-starter-kubernetes-client-config` or Actuator refresh bus. | **Native Container Volume Watching**: Built-in hot reloading on mounted config changes. |
| **Profile Activation Strictness** | Unknown profile strings fail silently or fallback to default. | **Strict Profile Checking**: Configurable compile/startup warnings for misspelled profile names. |

```java
// Spring Boot 4: Clean Immutable Record Configuration Properties
package com.example.config;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.validation.annotation.Validated;

@ConfigurationProperties(prefix = "app.payment")
@Validated
public record PaymentGatewayProperties(
    @NotBlank String apiKey,
    @Min(1000) int timeoutMillis,
    boolean sandboxMode
) {}
```

---

## 8. Primary Source & Further Reading

- [Spring Boot Reference: Profiles](https://docs.spring.io/spring-boot/reference/features/profiles.html) — Official documentation on profiles and activation.
- [Spring Boot Reference: Externalized Configuration](https://docs.spring.io/spring-boot/reference/features/external-config.html) — Complete 17-level property resolution hierarchy.
- Related Cheatsheet: [Spring Core & Annotations Cheatsheet](../cheatsheet/spring-core-annotations.md)

---

## 9. Knowledge Check & Retrieval Practice

??? question "Question 1: Which source takes precedence if the same property is set in `application-prod.yml` and an OS Environment Variable?"
    **Answer**: OS Environment Variables take precedence over profile-specific configuration files, allowing container overrides at runtime.

??? question "Question 2: What is the recommended way to set active profiles inside Docker and Kubernetes deployments?"
    **Answer**: Set the `SPRING_PROFILES_ACTIVE` environment variable within the container or Kubernetes deployment manifest specification.

??? question "Question 3: How can you register a bean so that it loads in every environment except production?"
    **Answer**: Annotate the bean class with `@Profile("!prod")` to exclude it when the production profile is active.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0004: Aspect-Oriented Programming (AOP)**](0004-aspect-oriented-programming-aop.md) | [**All Lessons**](index.md) | [➡️ **0006: Servlet Architecture vs DispatcherServlet**](0006-servlet-architecture-and-dispatcherservlet.md) |

💬 *Have any questions on Module 1? Ask anytime!*
