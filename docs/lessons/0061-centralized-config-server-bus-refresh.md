---
icon: lucide/sliders
---

# 0061: Centralized Configuration with Spring Cloud Config Server & Dynamic Bus Refresh

In a microservices ecosystem with dozens of services deployed across `dev`, `stage`, and `prod` environments, managing scattered `application.yml` files becomes an operational nightmare. Updating a feature flag or rotating a database password should never require rebuilding and redeploying container images across the cluster.

**Spring Cloud Config Server** provides HTTP resource-based, centralized external configuration management backed by Git or HashiCorp Vault. Combined with **Spring Cloud Bus** and Apache Kafka, configuration changes broadcast instantly to all running instances with zero application restarts.

In this lesson, you will master configuring the Config Server, connecting Config Clients using `spring.config.import`, using `@RefreshScope`, and broadcasting cluster-wide configuration reloads via Spring Cloud Bus.

---

## 1. Centralized Configuration & Bus Refresh Flow

``` mermaid
flowchart TD
    subgraph StorageLayer["Versioned Storage"]
        GitRepo["Git Repository (config-repo.git)"]
        AppProps["order-service-prod.yml"]
        GlobalProps["application.yml (Shared by all services)"]
        GitRepo --- AppProps
        GitRepo --- GlobalProps
    end

    subgraph ConfigServerTier["Spring Cloud Config Server (Port 8888)"]
        ConfigServer["Config Server (@EnableConfigServer)"]
    end

    subgraph MessageBus["Spring Cloud Bus (Kafka / RabbitMQ)"]
        BusTopic["Kafka Topic: 'springCloudBus'"]
    end

    subgraph ClientInstances["Order Service Cluster (Port 8081)"]
        subgraph Pod1["Order Service Instance 1"]
            Scope1["@RefreshScope Beans"]
            ActuatorRefresh["/actuator/busrefresh Webhook"]
        end
        subgraph Pod2["Order Service Instance 2"]
            Scope2["@RefreshScope Beans"]
        end
    end

    GitRepo -->|1. Pulls updated commits| ConfigServer
    ConfigServer -.->|2. Initial Bootstrap Config on Startup| Pod1
    ConfigServer -.->|2. Initial Bootstrap Config on Startup| Pod2

    DevOpsAdmin["DevOps / Git Webhook"] -->|3. POST /actuator/busrefresh| ActuatorRefresh
    ActuatorRefresh -->|4. Publish RefreshRemoteApplicationEvent| BusTopic
    BusTopic -->|5. Broadcast Refresh Event| Pod1
    BusTopic -->|5. Broadcast Refresh Event| Pod2
    
    Pod1 -->|6. Re-pull fresh properties & update| Scope1
    Pod2 -->|6. Re-pull fresh properties & update| Scope2
```

---

## 2. Setting Up Spring Cloud Config Server

### Dependencies (`pom.xml`)

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-config-server</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

### Application Bootstrap

```java
package com.example.configserver;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.config.server.EnableConfigServer;

@SpringBootApplication
@EnableConfigServer
public class ConfigServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(ConfigServerApplication.class, args);
    }
}
```

### Server Configuration (`application.yml`)

```yaml
server:
  port: 8888

spring:
  application:
    name: config-server
  cloud:
    config:
      server:
        git:
          uri: https://github.com/my-org/microservices-config-repo.git
          clone-on-start: true
          default-label: main
          search-paths: '{application}'
          # For private repositories:
          # username: oauth2
          # password: ${GITHUB_PAT_TOKEN}
```

---

## 3. Client Integration with `spring.config.import`

In Spring Boot 3.x, bootstrap properties are unified into standard `application.yml` via the `spring.config.import` directive:

### Client Dependencies (`pom.xml`)

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-config</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-bus-kafka</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

### Client Configuration (`application.yml`)

```yaml
spring:
  application:
    name: order-service
  profiles:
    active: prod
  # Import configuration from remote Config Server with optional fallback
  config:
    import: "optional:configserver:http://localhost:8888"

management:
  endpoints:
    web:
      exposure:
        include: health,info,refresh,busrefresh
```

---

## 4. Dynamic Reloading with `@RefreshScope`

Beans annotated with `@RefreshScope` are lazily recreated upon receiving a refresh event, dynamically injecting modified configuration properties without dropping user connections:

```java
package com.example.service;

import lombok.Getter;
import lombok.Setter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Service;

@Getter
@Setter
@Service
@RefreshScope
public class OrderPricingService {

    @Value("${pricing.discount.percentage:0.0}")
    private double discountPercentage;

    @Value("${feature.flags.express-checkout-enabled:false}")
    private boolean expressCheckoutEnabled;

    public double calculateFinalPrice(double originalPrice) {
        return originalPrice * (1.0 - (discountPercentage / 100.0));
    }
}
```

---

## 5. Cluster-Wide Dynamic Refresh via Spring Cloud Bus

When running 20 instances of `order-service`, calling individual `/actuator/refresh` on each IP is impossible. **Spring Cloud Bus** links instances via a Kafka or RabbitMQ event topic:

```bash
# 1. Update git repository:
git commit -am "Update discount.percentage to 15.0" && git push origin main

# 2. Trigger busrefresh webhook on ANY single service instance or gateway:
curl -X POST http://api-gateway:8080/actuator/busrefresh

# Output:
# Spring Cloud Bus publishes a RefreshRemoteApplicationEvent to Kafka.
# All 20 instances consume the event, re-pull git properties, and update @RefreshScope beans simultaneously.
```

---

## 6. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Config Import** | `spring.config.import` syntax with standard property binders. | Zero-overhead streaming config watchers via HTTP/2 and gRPC server streams. |
| **Encrypted Secrets** | Symmetric/Asymmetric RSA key decryption in Config Server. | First-class native integration with HashiCorp Vault, AWS KMS, and GCP Secret Manager. |
| **GraalVM Native Image** | Requires reflection hints for `@ConfigurationProperties` and `@RefreshScope`. | AOT compilation with dynamic proxy proxies for refreshable beans. |

---

## 7. Primary Sources & Further Reading

- [Spring Cloud Config Official Reference](https://docs.spring.io/spring-cloud-config/reference/) — Git, Vault, and File backend setups.
- [Spring Cloud Bus Documentation](https://docs.spring.io/spring-cloud-bus/reference/) — Event broadcasting with Kafka and RabbitMQ.
- [Spring Boot Externalized Configuration](https://docs.spring.io/spring-boot/reference/features/external-config.html#features.external-config.files.configtree).

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the purpose of `@RefreshScope` in a Spring Cloud microservice?"
    **Answer**: It marks a Spring bean to be dynamically re-instantiated with new property values when a refresh event occurs, avoiding the need to restart the JVM.

??? question "Question 2: How does Spring Cloud Bus optimize configuration reloading across a horizontally scaled cluster?"
    **Answer**: It broadcasts a single `RefreshRemoteApplicationEvent` over a message broker (like Kafka) so a single webhook call updates all running instances simultaneously.

??? question "Question 3: How does Spring Boot 3 resolve configuration from Config Server without `bootstrap.yml`?"
    **Answer**: By using the standardized `spring.config.import: "configserver:http://..."` property inside the standard `application.yml` file.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0060: API Gateway Routing & Security with Spring Cloud Gateway**](0060-api-gateway-routing-security-spring-cloud.md) | [**All Lessons**](index.md) | [➡️ **0062: Distributed Tracing with Micrometer & Zipkin**](0062-distributed-tracing-micrometer-zipkin.md) |

🎉 **Lesson 0061 completed! Proceed to Lesson 0062 to master distributed tracing with Micrometer Tracing and Zipkin/Tempo.**
