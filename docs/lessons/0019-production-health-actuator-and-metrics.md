---
icon: lucide/activity
---

# 0019: Production Health, Actuator Metrics & Prometheus Observability

In modern microservices and Kubernetes clusters, software must be **observable by default**. If your service begins leaking memory, starving database connections, or degrading response times, operations engineers and automated orchestration systems must detect it before customers do.

**Spring Boot Actuator** and **Micrometer** form the enterprise backbone for production monitoring. In this lesson, you will master Actuator endpoint configuration, implement **Custom Health Indicators**, configure **Kubernetes Liveness and Readiness Probes**, instrument custom business metrics with **Micrometer**, and export Prometheus telemetry.

---

## 1. The Actuator Observability Architecture

Actuator exposes operational endpoints over HTTP and JMX, providing real-time visibility into the running JVM, Spring `ApplicationContext`, thread pools, and connected infrastructure:

``` mermaid
flowchart TD
    subgraph SpringApp["🚀 Spring Boot Microservice"]
        ActuatorCore["⚡ Spring Boot Actuator"]
        MicrometerRegistry["📊 Micrometer MeterRegistry"]
        HealthGroup["🩺 Health Indicators & Probes"]
        
        ActuatorCore --> HealthGroup
        ActuatorCore --> MicrometerRegistry
    end

    K8s["☸️ Kubernetes Kubelet"] -->|GET /actuator/health/liveness| HealthGroup
    K8s -->|GET /actuator/health/readiness| HealthGroup
    
    Prometheus["📈 Prometheus Scraper"] -->|GET /actuator/prometheus| MicrometerRegistry
    Grafana["🖥️ Grafana Dashboards"] --> Prometheus
    
    Ops["👨‍💻 SRE / On-Call"] -->|GET /actuator/metrics| ActuatorCore
```

---

## 2. Dependency & Endpoint Configuration

Add `spring-boot-starter-actuator` and the `micrometer-registry-prometheus` bridge:

```xml
<dependencies>
    <!-- Core Actuator -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>
    
    <!-- Prometheus Registry Export -->
    <dependency>
        <groupId>io.micrometer</groupId>
        <artifactId>micrometer-registry-prometheus</artifactId>
        <scope>runtime</scope>
    </dependency>
</dependencies>
```

### Production Endpoint Exposure (`application.yml`)

By default, only `/health` is exposed over HTTP for security reasons. Configure which endpoints to publish:

```yaml
management:
  endpoints:
    web:
      base-path: /actuator
      exposure:
        include: ["health", "info", "metrics", "prometheus", "loggers"]
  endpoint:
    health:
      show-details: when_authorized
      probes:
        enabled: true # Enables Kubernetes liveness and readiness probes
  metrics:
    tags:
      application: ${spring.application.name:order-service}
      environment: ${SPRING_PROFILES_ACTIVE:production}
```

---

## 3. Kubernetes Probes: Liveness vs Readiness

Kubernetes relies on two distinct health signals to manage pod lifecycles:

``` mermaid
sequenceDiagram
    autonumber
    participant K8s as Kubernetes Kubelet
    participant Pod as Spring Boot Pod (:8080)
    participant DB as PostgreSQL Database

    Note over K8s,Pod: 1. Liveness Probe Check
    K8s->>Pod: GET /actuator/health/liveness
    Pod-->>K8s: 200 OK (Status: UP)
    Note over K8s: Pod is alive. Do not restart container.

    Note over K8s,Pod: 2. Readiness Probe Check
    K8s->>Pod: GET /actuator/health/readiness
    Pod->>DB: Check DB Connection Pool
    alt Database Available
        Pod-->>K8s: 200 OK (Status: UP)
        Note over K8s: Send customer traffic to this Pod.
    else Database Unreachable
        Pod-->>K8s: 503 SERVICE UNAVAILABLE (Status: DOWN)
        Note over K8s: Remove Pod from Ingress load balancer!<br/>(Do not restart yet).
    end
```

| Probe Type | Endpoint | Purpose | Action When `DOWN` |
| :--- | :--- | :--- | :--- |
| **Liveness** | `/actuator/health/liveness` | Checks if the internal JVM state is alive (no unrecoverable deadlocks). | Kubernetes **kills and restarts** the container. |
| **Readiness** | `/actuator/health/readiness` | Checks if the application is ready to accept user traffic (DB connected, caches warm). | Kubernetes **stops routing traffic** until ready. |

---

## 4. Custom Health Indicators

When your service depends on external third-party APIs (e.g. Stripe, PayPal, SendGrid), implement `HealthIndicator` to include them in health checks:

```java
package com.example.demo.health;

import org.springframework.boot.actuate.health.Health;
import org.springframework.boot.actuate.health.HealthIndicator;
import org.springframework.stereotype.Component;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

@Component
public class PaymentGatewayHealthIndicator implements HealthIndicator {

    private final HttpClient httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofMillis(1500))
            .build();

    @Override
    public Health health() {
        try {
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create("https://api.payment-gateway.internal/health"))
                    .timeout(Duration.ofMillis(2000))
                    .GET()
                    .build();

            HttpResponse<Void> response = httpClient.send(request, HttpResponse.BodyHandlers.discarding());

            if (response.statusCode() == 200) {
                return Health.up()
                        .withDetail("gateway", "Stripe API")
                        .withDetail("responseTimeMs", 45)
                        .build();
            } else {
                return Health.down()
                        .withDetail("gateway", "Stripe API")
                        .withDetail("httpStatus", response.statusCode())
                        .build();
            }
        } catch (Exception e) {
            return Health.down(e)
                    .withDetail("gateway", "Stripe API")
                    .withDetail("error", "Gateway ping timeout or connection refused")
                    .build();
        }
    }
}
```

---

## 5. Custom Business Metrics with Micrometer

**Micrometer** is the vendor-neutral metrics facade for JVM applications (the "SLF4J for metrics"). It translates measurements into dimensional formats for Prometheus, Datadog, InfluxDB, and New Relic.

### Core Meter Types:
- **`Counter`**: Monotonically increasing value (e.g. `orders_placed_total`).
- **`Timer`**: Measures execution duration and latency distributions (e.g. `checkout_duration_seconds`).
- **`Gauge`**: Value that can go up and down (e.g. `active_websocket_connections`).

```java
package com.example.demo.service;

import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;

@Service
public class OrderCheckoutService {

    private final Counter orderSuccessCounter;
    private final Counter orderFailureCounter;
    private final Timer checkoutTimer;

    public OrderCheckoutService(MeterRegistry registry) {
        this.orderSuccessCounter = Counter.builder("business.orders.placed")
                .tag("type", "ecommerce")
                .description("Total number of successfully placed orders")
                .register(registry);

        this.orderFailureCounter = Counter.builder("business.orders.failed")
                .tag("type", "ecommerce")
                .description("Total number of failed order attempts")
                .register(registry);

        this.checkoutTimer = Timer.builder("business.checkout.latency")
                .tag("layer", "service")
                .description("Latency distribution of checkout operations")
                .publishPercentiles(0.5, 0.95, 0.99) // p50, p95, p99 latency SLA
                .register(registry);
    }

    public void processCheckout(String customerId, BigDecimal amount) {
        checkoutTimer.record(() -> {
            try {
                // Execute business logic
                executePaymentAndFulfillment(customerId, amount);
                orderSuccessCounter.increment();
            } catch (Exception ex) {
                orderFailureCounter.increment();
                throw ex;
            }
        });
    }

    private void executePaymentAndFulfillment(String customerId, BigDecimal amount) {
        // Business logic execution...
    }
}
```

---

## 6. Prometheus Scrape Output Format

Navigating to `GET /actuator/prometheus` yields dimensional metrics scraped by Prometheus:

```text
# HELP business_orders_placed_total Total number of successfully placed orders
# TYPE business_orders_placed_total counter
business_orders_placed_total{application="order-service",environment="production",type="ecommerce"} 1420.0

# HELP business_checkout_latency_seconds Latency distribution of checkout operations
# TYPE business_checkout_latency_seconds summary
business_checkout_latency_seconds{application="order-service",environment="production",layer="service",quantile="0.5"} 0.042
business_checkout_latency_seconds{application="order-service",environment="production",layer="service",quantile="0.95"} 0.185
business_checkout_latency_seconds{application="order-service",environment="production",layer="service",quantile="0.99"} 0.490
business_checkout_latency_seconds_count{application="order-service",environment="production",layer="service"} 1420.0
```

---

## 7. Primary Sources & Further Reading

- [Spring Boot Actuator Reference](https://docs.spring.io/spring-boot/reference/actuator/index.html) — Endpoints, metrics, and security.
- [Micrometer Core Documentation](https://micrometer.io/docs/concepts) — Concepts of Counters, Timers, Gauges, and percentiles.
- [Kubernetes Pod Lifecycle: Container Probes](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-probes) — Liveness and readiness probe mechanics.

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the fundamental operational difference between Kubernetes Liveness and Readiness probes?"
    **Answer**: Liveness probes trigger pod restarts when the internal JVM state is unrecoverable, while Readiness probes temporarily remove pods from traffic routing when dependencies are unavailable.

??? question "Question 2: What is the purpose of the Micrometer `publishPercentiles(0.5, 0.95, 0.99)` configuration on a `Timer`?"
    **Answer**: It pre-calculates the 50th, 95th, and 99th percentile execution durations locally, enabling accurate SLA latency analysis without high server aggregation overhead.

??? question "Question 3: Why should `/actuator/env` and `/actuator/heapdump` never be exposed to public unauthenticated traffic?"
    **Answer**: They expose critical system secrets (passwords, tokens) and internal memory dumps containing customer PII, creating severe security and compliance vulnerabilities.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0018: Spring Boot DevTools & LiveReload**](0018-spring-boot-devtools-and-livereload.md) | [**All Lessons**](index.md) | [➡️ **0020: OpenAPI 3 & Swagger UI Documentation**](0020-openapi-3-and-swagger-ui-documentation.md) |
