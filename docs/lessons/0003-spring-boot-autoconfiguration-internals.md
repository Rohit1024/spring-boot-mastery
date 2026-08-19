---
icon: lucide/cpu
---

# 0003: Spring Boot under the hood: Auto-configuration and starters

Before Spring Boot, configuring a Spring application required writing hundreds of lines of XML or verbose `@Configuration` classes just to set up a `DispatcherServlet`, a `DataSource`, or an `ObjectMapper`.

Spring Boot replaces manual configuration with auto-configuration. This lesson covers how `@SpringBootApplication` boots, how auto-configuration scans the classpath, and how `@Conditional` annotations let you override defaults.

---

## 1. Dissecting `@SpringBootApplication`

When you create a Spring Boot project, the main entry point is marked with `@SpringBootApplication`:

```java
@SpringBootApplication
public class Application {
    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

Under the hood, `@SpringBootApplication` is a **composite annotation** combining three core meta-annotations:

``` mermaid
flowchart TD
    SBA["@SpringBootApplication"]
    
    SBA --> SBC["@SpringBootConfiguration<br/><i>(Specialized @Configuration for Spring Boot)</i>"]
    SBA --> EAC["@EnableAutoConfiguration<br/><i>(Enables Spring Boot's Auto-Configuration engine)</i>"]
    SBA --> CS["@ComponentScan<br/><i>(Scans for @Component, @Service, @Repository in current package & sub-packages)</i>"]
```

---

## 2. How auto-configuration works internally

Auto-configuration is not magic, it is a deterministic, two-phase process:

``` mermaid
sequenceDiagram
    autonumber
    participant App as Spring Boot Startup
    participant Imports as AutoConfiguration.imports
    participant Engine as ConditionEvaluationReport
    participant Ctx as ApplicationContext

    App->>Imports: 1. Read META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
    Imports-->>Engine: 2. List of 150+ Candidate Auto-Configs (DataSource, Web, Security, Jackson...)
    loop For each Auto-Configuration class
        Engine->>Engine: 3. Evaluate @Conditional annotations (@ConditionalOnClass, @ConditionalOnMissingBean)
        alt All Conditions PASS (true)
            Engine->>Ctx: 4. Register Default Infrastructure Beans
        else Any Condition FAILS (false)
            Engine->>Engine: 5. Skip configuration silently
        end
    end
    App->>Ctx: 6. ApplicationContext Ready!
```

### The import discovery file
In Spring Boot 3.x, all auto-configurations are registered in:
`META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`

---

## 3. The `@Conditional` annotation family

Spring Boot's auto-configuration relies on conditional bean registration. Here are the core conditional triggers:

| Annotation | Trigger Condition | Real-World Use Case |
| :--- | :--- | :--- |
| **`@ConditionalOnClass`** | Target class exists on classpath | Auto-configure Jackson if `com.fasterxml.jackson.databind.ObjectMapper` is in JARs |
| **`@ConditionalOnMissingBean`** | No bean of this type exists in Context | Provides fallback default bean **only if you didn't define one yourself** |
| **`@ConditionalOnProperty`** | Matches specific `application.properties` key/value | Enables Redis caching only if `spring.cache.type=redis` |
| **`@ConditionalOnWebApplication`** | Running in a Servlet or Reactive Web environment | Registers `DispatcherServlet` only in web apps |

---

## 4. Real-world deep dive: Inside `JacksonAutoConfiguration`

Let's see how Spring Boot auto-configures the JSON `ObjectMapper`:

```java
@AutoConfiguration
@ConditionalOnClass(ObjectMapper.class) // Only run if Jackson JAR is present
public class JacksonAutoConfiguration {

    @Bean
    @Primary
    @ConditionalOnMissingBean // Only create this default ObjectMapper if YOU didn't define one!
    public ObjectMapper jacksonObjectMapper(Jackson2ObjectMapperBuilder builder) {
        return builder.createXmlMapper(false).build();
    }
}
```

### How you override default behavior
Because Spring Boot uses `@ConditionalOnMissingBean`, you can completely override the default `ObjectMapper` simply by declaring your own `@Bean`:

```java
@Configuration
public class CustomJacksonConfig {

    @Bean
    public ObjectMapper customObjectMapper() {
        return JsonMapper.builder()
                .findAndAddModules()
                .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, false)
                .build();
    }
}
```
*When Spring Boot evaluates `JacksonAutoConfiguration`, `@ConditionalOnMissingBean` evaluates to **false**, and Spring Boot quietly steps aside!*

---

## 5. Building your own custom auto-configuration

Imagine your company requires an audit logging client auto-configured in every microservice.

### Step 1: Define the service
```java
public class AuditClient {
    private final String serviceName;

    public AuditClient(String serviceName) {
        this.serviceName = serviceName;
    }

    public void log(String event) {
        System.out.printf("[%s AUDIT] %s%n", serviceName, event);
    }
}
```

### Step 2: Write the auto-configuration with conditions
```java
@AutoConfiguration
@ConditionalOnProperty(name = "company.audit.enabled", havingValue = "true", matchIfMissing = true)
public class AuditAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean
    public AuditClient auditClient(@Value("${spring.application.name:unknown-service}") String appName) {
        return new AuditClient(appName);
    }
}
```

### Step 3: Register in `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`
```properties
com.company.audit.AuditAutoConfiguration
```

---

## 6. Inspecting the condition evaluation report

To see why an auto-configuration ran or was skipped, run your app with `--debug` or inspect `/actuator/conditions`:

```bash
java -jar app.jar --debug
```

```text
============================
CONDITIONS EVALUATION REPORT
============================

Positive matches:
-----------------
   JacksonAutoConfiguration matched:
      - @ConditionalOnClass found required class 'com.fasterxml.jackson.databind.ObjectMapper'

Negative matches:
-----------------
   MongoDataAutoConfiguration:
      Did not match:
         - @ConditionalOnClass did not find required class 'com.mongodb.client.MongoClient'
```

---

## 7. Spring Boot 3 vs Spring Boot 4: Auto-configuration evolution

Spring Boot 4 optimizes auto-configuration discovery for instant startup times and native images:

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        ImportsFile["AutoConfiguration.imports (Runtime File Read)"]
        ReflectionCond["Runtime Reflection Condition Checks"]
        AllInOne["Monolithic Starter Packages"]
    end

    subgraph SB4["Spring Boot 4.x"]
        AOTIndex["AOT Generated AutoConfig Index"]
        StaticCond["Compile-Time Condition Pruning"]
        ModularStarters["Fine-Grained Modular Starters"]
    end

    SB3 ==>|Build-Time Acceleration| SB4
```

### Key differences and configuration comparison

| Auto-Configuration Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Registration Mechanism** | `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` | **AOT Pre-Compiled Auto-Configuration Index**: Scanned and verified at compile-time. |
| **Condition Evaluation** | Evaluated dynamically at JVM boot using reflection. | **Hybrid Static/Dynamic Evaluation**: Unmatched starters are pruned before classloading. |
| **Legacy `spring.factories`** | Deprecated for auto-configuration (still allowed for initializers). | **Fully Removed**: Hard error if legacy `spring.factories` auto-config entries are found. |
| **Starter Modularity** | Starters bundle broad transitives (e.g. all of Jackson + Tomcat). | **Modularized Component Starters** (e.g. `spring-boot-starter-web-minimal`, virtual thread native). |

---

## 8. Primary sources and further reading

- [Spring Boot Reference: Creating Your Own Auto-Configuration](https://docs.spring.io/spring-boot/reference/features/developing-auto-configuration.html), Official guide on conditional loading.
- Related Cheatsheet: [Spring Core & Annotations Cheatsheet](../cheatsheet/spring-core-annotations.md)

---

## 9. Knowledge check and practice

??? question "Question 1: What is the primary purpose of `@ConditionalOnMissingBean` in Spring Boot's internal starters?"
    **Answer**: It registers default framework beans while allowing developers to provide their own custom bean overrides seamlessly.

??? question "Question 2: What three core annotations make up `@SpringBootApplication` under the hood?"
    **Answer**: `@SpringBootConfiguration` provides configuration capabilities, `@EnableAutoConfiguration` activates auto-configuration, and `@ComponentScan` discovers project components.

??? question "Question 3: Where must custom Auto-Configuration classes be registered in Spring Boot 3.x?"
    **Answer**: In the classpath file `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0002: Dependency Injection Strategies**](0002-dependency-injection-strategies.md) | [**All Lessons**](index.md) | [**0004: Aspect-Oriented Programming (AOP)**](0004-aspect-oriented-programming-aop.md) |

