---
icon: lucide/compass
---

# 0059: Service Registry & Discovery with Spring Cloud Netflix Eureka

In static architectures, servers have fixed IP addresses configured in properties files. In modern cloud and containerized environments, instances auto-scale, crash, restart, and receive dynamic, ephemeral IP addresses continuously. Hardcoding hostnames or IPs leads to fragile networks and broken routing.

**Service Discovery** solves this by providing a dynamic lookup directory where microservices register their network coordinates upon startup and discover healthy downstream peers at runtime.

In this lesson, you will master configuring a Spring Cloud Eureka Server, registering Eureka Clients, tuning heartbeats and self-preservation modes, and integrating client-side load balancing.

---

## 1. Service Discovery Architecture

``` mermaid
flowchart TD
    subgraph RegistryTier["Service Registry (Spring Cloud Eureka Server)"]
        EurekaServer["Eureka Server (Registry Directory on Port 8761)"]
        RegistryMap["Internal Directory Map: 'PAYMENT-SERVICE' -> [10.0.1.25:8082, 10.0.1.26:8082]"]
        EurekaServer --- RegistryMap
    end

    subgraph ProducerMicroservices["Payment Microservice Instances"]
        PaymentInst1["Payment Service (Pod 1: 10.0.1.25:8082)"]
        PaymentInst2["Payment Service (Pod 2: 10.0.1.26:8082)"]
        
        PaymentInst1 -->|1. Register & Send Heartbeat every 30s| EurekaServer
        PaymentInst2 -->|1. Register & Send Heartbeat every 30s| EurekaServer
    end

    subgraph ConsumerMicroservices["Order Microservice (Caller)"]
        OrderApp["Order Service (Pod 10.0.2.10)"]
        LocalCache["Local Eureka Cache (Refreshed every 30s)"]
        LoadBalancer["Spring Cloud LoadBalancer (Round Robin)"]
        
        OrderApp -->|2. Fetch Registry Updates| EurekaServer
        EurekaServer -.->|Return Active Instances| LocalCache
        LocalCache --> LoadBalancer
        LoadBalancer -->|3. Route Request directly to Pod 1| PaymentInst1
    end
```

---

## 2. Setting Up Eureka Server (`eureka-server`)

### Dependencies (`pom.xml`)

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-server</artifactId>
</dependency>
```

### Application Bootstrap

```java
package com.example.eurekaserver;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.netflix.eureka.server.EnableEurekaServer;

@SpringBootApplication
@EnableEurekaServer
public class EurekaServerApplication {
    public static void main(String[] args) {
        SpringApplication.run(EurekaServerApplication.class, args);
    }
}
```

### Server Configuration (`application.yml`)

```yaml
server:
  port: 8761

spring:
  application:
    name: eureka-server

eureka:
  instance:
    hostname: localhost
  client:
    # Standalone Eureka Server does not need to register with itself
    register-with-eureka: false
    fetch-registry: false
  server:
    # Disable self-preservation in development to immediately evict dead pods
    enable-self-preservation: true
    eviction-interval-timer-in-ms: 10000
```

---

## 3. Registering Microservices as Eureka Clients

### Dependencies (`pom.xml`)

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-netflix-eureka-client</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-loadbalancer</artifactId>
</dependency>
```

### Client Configuration (`application.yml`)

```yaml
server:
  port: 8082

spring:
  application:
    name: payment-service

eureka:
  client:
    service-url:
      defaultZone: http://localhost:8761/eureka/
    fetch-registry: true
    register-with-eureka: true
  instance:
    prefer-ip-address: true
    # Heartbeat configuration: Send heartbeat every 10 seconds
    lease-renewal-interval-in-seconds: 10
    # Evict if no heartbeat received for 30 seconds
    lease-expiration-duration-in-seconds: 30
```

---

## 4. Eureka Self-Preservation Mode

> [!IMPORTANT]
> **What is Self-Preservation Mode?**
> During sudden network partitions, instances may still be healthy, but unable to reach the Eureka Server. If the Eureka server suddenly loses >15% of heartbeats in 15 minutes, it activates **Self-Preservation Mode**:
> - It **stops evicting expired instances** to avoid purging healthy pods during temporary network blips.
> - Clients rely on client-side retry/circuit breakers if an instance happens to be dead.
> - In local development (`dev` profile), disable it (`enable-self-preservation: false`) so killed processes disappear immediately from the dashboard.

---

## 5. Eureka vs Kubernetes Native DNS Discovery

In cloud-native architectures, teams often contrast Spring Cloud Eureka with Kubernetes-native Service Discovery:

| Dimension | Spring Cloud Eureka | Kubernetes Native (Kube-DNS / CoreDNS) |
| :--- | :--- | :--- |
| **Control Plane** | Dedicated Eureka Server JVM application. | Built-in Kubernetes `Service` and `CoreDNS`. |
| **Discovery Mechanism** | Application-level REST registry caching. | OS-level DNS resolution (`http://payment-service:8080`). |
| **Load Balancing** | Client-side (Spring Cloud LoadBalancer). | Server-side / Proxy (Kube-Proxy `iptables` / IPVS). |
| **Multi-Language Support** | Primarily JVM / Spring Boot ecosystem. | Polyglot (Go, Node, Python, Java). |
| **Ideal Deployment** | Virtual machines, bare metal, AWS EC2, or hybrid cloud. | Containerized Kubernetes clusters (EKS, GKE, AKS). |

---

## 6. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Eureka Client Starter** | Uses Jakarta EE 10 baseline with Jersey 3 client bindings. | Lightweight HTTP/2 and gRPC transport layer replacing legacy Jersey REST calls. |
| **Kubernetes Convergence** | `spring-cloud-starter-kubernetes-discovery` for hybrid setups. | Native Kubernetes controller watch streaming without polling loops. |
| **AOT Compilation** | Requires custom Reachability metadata for Eureka reflection. | Full GraalVM native image compatibility for instant Eureka client startup. |

---

## 7. Primary Sources & Further Reading

- [Spring Cloud Netflix Official Documentation](https://docs.spring.io/spring-cloud-netflix/reference/) — Eureka Server and Client configuration.
- [Netflix Eureka GitHub Wiki](https://github.com/Netflix/eureka/wiki) — Self-preservation algorithms and peer replication protocol.
- [Spring Cloud Commons Service Discovery](https://docs.spring.io/spring-cloud-commons/reference/spring-cloud-commons/discovery-client.html).

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the primary role of a Service Registry in a microservices ecosystem?"
    **Answer**: To dynamically track and provide the changing IP addresses and ports of running microservice instances so callers do not rely on hardcoded network locations.

??? question "Question 2: What is Eureka's Self-Preservation mode designed to protect against?"
    **Answer**: Network partitions where healthy microservice instances are temporarily unable to send heartbeats, preventing Eureka from mistakenly evicting all running instances.

??? question "Question 3: How does Client-Side Load Balancing work with Eureka and Spring Cloud LoadBalancer?"
    **Answer**: The client periodically downloads the entire active instance registry from Eureka and distributes outbound requests across healthy pods using a local algorithm like round-robin.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0058: Inter-Service Communication: Feign, WebClient & RestTemplate**](0058-interservice-communication-feign-webclient.md) | [**All Lessons**](index.md) | [➡️ **0060: API Gateway Routing & Security with Spring Cloud Gateway**](0060-api-gateway-routing-security-spring-cloud.md) |

🎉 **Lesson 0059 completed! Proceed to Lesson 0060 to master edge routing, cross-cutting filters, and rate limiting with Spring Cloud Gateway.**
