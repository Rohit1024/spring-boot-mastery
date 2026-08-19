---
icon: lucide/git-branch
---

# 0062: Distributed tracing with Micrometer Tracing and Zipkin

In a microservices architecture, a single user request can trigger a cascading web of synchronous HTTP calls, asynchronous Kafka events, and database transactions across 8 distinct microservices. When a request suddenly takes 3.8 seconds to complete or fails with an intermittent 500 error, inspecting isolated log files across individual servers is practically impossible.

**Distributed Tracing** tracks the complete lifecycle of a request as it hops across network boundaries, assembling a visual call-graph waterfall with sub-millisecond timing per hop.

In this lesson, you will master the transition from legacy Spring Cloud Sleuth to **Micrometer Tracing**, propagate W3C `traceparent` contexts across OpenFeign and Kafka, and visualize traces in Zipkin.

---

## 1. Distributed trace waterfall architecture

``` mermaid
flowchart TD
    subgraph ClientRequest["Incoming Client Call"]
        ClientReq["HTTP POST /api/v1/orders (Total Latency: 320ms)"]
    end

    subgraph TraceJourney["Distributed Trace: traceId=4bf92f3577b34da6"]
        
        subgraph Span1["Span 1: API Gateway (Duration: 320ms)"]
            GW["Spring Cloud Gateway (spanId=00f067aa)"]
        end
        
        subgraph Span2["Span 2: Order Service (Duration: 280ms)"]
            OrderSvc["Order Service (spanId=5a12cd89, parentSpanId=00f067aa)"]
        end
        
        subgraph Span3["Span 3: Payment Service (Duration: 190ms - Bottleneck)"]
            PaymentSvc["Payment Service (spanId=98eef410, parentSpanId=5a12cd89)"]
            ThirdPartyAPI["External Stripe Gateway (Duration: 175ms)"]
            PaymentSvc --> ThirdPartyAPI
        end
        
        subgraph Span4["Span 4: Kafka Event Publication (Duration: 12ms)"]
            KafkaPublish["Kafka: 'order-created' (spanId=33ba7701, parentSpanId=5a12cd89)"]
        end
        
        GW -->|W3C traceparent Header| OrderSvc
        OrderSvc -->|OpenFeign HTTP Call| PaymentSvc
        OrderSvc -->|Kafka Record Header| KafkaPublish
    end

    subgraph APMCollector["Observability & Tracing Backend"]
        ZipkinServer["Zipkin Server / Grafana Tempo (Port 9411)"]
    end

    ClientReq --> GW
    GW -.->|Export Spans asynchronously| ZipkinServer
    OrderSvc -.->|Export Spans asynchronously| ZipkinServer
    PaymentSvc -.->|Export Spans asynchronously| ZipkinServer
```

---

## 2. Spring Cloud Sleuth vs Micrometer tracing

In Spring Boot 3.x, the legacy **Spring Cloud Sleuth** library was deprecated and rewritten as **Micrometer Tracing**:

| Capability | Spring Boot 2.x (Spring Cloud Sleuth) | Spring Boot 3.x / 4.x (Micrometer Tracing) |
| :--- | :--- | :--- |
| **Core Architecture** | Coupled directly to Brave or Sleuth-native abstractions. | Vendor-neutral facade supporting OpenTelemetry (OTel) and Brave engines. |
| **Context Propagation** | B3 propagation headers (`X-B3-TraceId`, `X-B3-SpanId`). | W3C standard `traceparent` headers by default (`00-{traceId}-{spanId}-{flags}`). |
| **Logging Correlation** | Automatic MDC injection: `[appName,traceId,spanId,exportable]`. | Unified SLF4J MDC injection configured via `logging.pattern.level`. |

---

## 3. Maven dependencies (`pomxml`)

Include the Micrometer OpenTelemetry bridge and the Zipkin reporting exporter:

```xml
<!-- Micrometer Tracing Core Facade -->
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-otel</artifactId>
</dependency>

<!-- Exporter to send spans to Zipkin / Jaeger / Tempo over HTTP -->
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-exporter-zipkin</artifactId>
</dependency>

<!-- Actuator for Metrics & Health -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

---

## 4. Configuration (`applicationyml`)

Configure 100% trace sampling for development and point to the Zipkin collector:

```yaml
server:
  port: 8081

spring:
  application:
    name: order-service

management:
  tracing:
    sampling:
      # Probability of tracing requests (1.0 = 100% of requests; 0.1 = 10% in high-scale prod)
      probability: 1.0
    propagation:
      # W3C TraceContext standard
      type: W3C
  zipkin:
    tracing:
      endpoint: http://localhost:9411/api/v2/spans

logging:
  pattern:
    # Inject traceId and spanId directly into SLF4J log lines
    level: "%5p [${spring.application.name:},%X{traceId:-},%X{spanId:-}]"
```

---

## 5. Correlated structured logging in action

With Micrometer Tracing enabled, every log message automatically captures the active `traceId` and `spanId`:

```text
2026-08-17 14:22:01.412  INFO [order-service,4bf92f3577b34da6,5a12cd89] 48102 --- [nio-8081-exec-1] c.e.service.OrderService: Placing order for customer: CUST-901
2026-08-17 14:22:01.450  INFO [order-service,4bf92f3577b34da6,5a12cd89] 48102 --- [nio-8081-exec-1] c.e.client.PaymentClient: Invoking downstream payment service...
```

When checking logs in Elasticsearch/Loki, querying for `traceId: "4bf92f3577b34da6"` reveals every single log line printed by Gateway, Order Service, and Payment Service for that specific user request.

---

## 6. Creating custom spans programmatically

For expensive internal algorithms or complex database loops, create manual sub-spans:

```java
package com.example.service;

import io.micrometer.tracing.Span;
import io.micrometer.tracing.Tracer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class FraudDetectionService {

    private final Tracer tracer;

    public boolean evaluateFraudRisk(String customerId, double amount) {
        // Start a custom programmatic span
        Span customSpan = tracer.nextSpan().name("fraud-rule-engine").start();
        
        try (Tracer.SpanInScope ws = tracer.withSpan(customSpan.tag("customer.id", customerId))) {
            log.info("Executing custom neural fraud model evaluation...");
            Thread.sleep(45); // Simulating algorithmic computation
            return false;
        } catch (Exception e) {
            customSpan.error(e);
            throw new RuntimeException("Fraud evaluation failed", e);
        } finally {
            customSpan.end(); // Durably record duration and emit to Zipkin
        }
    }
}
```

---

## 7. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Tracing Engine** | `micrometer-tracing-bridge-otel` with OpenTelemetry Java SDK. | Native OpenTelemetry OTLP tracing without intermediate bridge translation layers. |
| **Virtual Threads Context** | ThreadLocal MDC context propagation requires custom task decorators. | First-class Scoped Values (`ScopedValue`) propagating tracing context across Virtual Threads. |
| **Zero-Configuration OTLP** | Requires `opentelemetry-exporter-zipkin` or OTLP gRPC dependencies. | Native Spring Boot auto-configuration for OpenTelemetry Protocol (OTLP). |

---

## 8. Primary sources and further reading

- [Micrometer Tracing Official Reference Guide](https://micrometer.io/docs/tracing), Spans, Tracers, and Baggage.
- [W3C TraceContext Specification](https://www.w3.org/TR/trace-context/), `traceparent` and `tracestate` header standards.
- [OpenZipkin Documentation](https://zipkin.io/), Zipkin UI, span formats, and distributed call graphs.

---

## 9. Knowledge check and practice

??? question "Question 1: What is the relationship between a Trace and a Span in distributed tracing?"
    **Answer**: A Trace represents the entire end-to-end request journey across multiple services, while a Span represents an individual timed unit of execution within a single service.

??? question "Question 2: What replaced Spring Cloud Sleuth in Spring Boot 3.x?"
    **Answer**: Micrometer Tracing, which acts as a vendor-neutral facade over tracing engines like OpenTelemetry and Brave.

??? question "Question 3: How does the W3C `traceparent` header propagate context across microservices?"
    **Answer**: It encodes the version, unique `trace-id`, calling `parent-span-id`, and trace flags in a standardized HTTP header format understood by all services and gateways.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0061: Centralized Config Server & Dynamic Bus Refresh**](0061-centralized-config-server-bus-refresh.md) | [**All Lessons**](index.md) | [ **0063: Fault Tolerance with Resilience4j**](0063-fault-tolerance-resilience4j.md) |

🎉 **Lesson 0062 completed! Proceed to Lesson 0063 to master fault tolerance, circuit breakers, and retries with Resilience4j.**
