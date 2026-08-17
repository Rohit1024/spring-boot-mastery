---
icon: lucide/git-commit
---

# 0047: OpenTelemetry (OTel): Vendor-Neutral Tracing, Spans & OTLP Collectors

In distributed microservice architectures, a single user click cascades across dozens of downstream services, database queries, and message brokers. When a request fails or suffers high latency, debugging without end-to-end distributed tracing is impossible.

Historically, organizations were forced into proprietary vendor lock-in (Datadog, New Relic, Dynatrace) by installing vendor-specific bytecode agents.

**OpenTelemetry (OTel)** is the CNCF industry standard that provides a **vendor-neutral observability framework** for collecting, processing, and exporting **Metrics, Traces, and Logs** via the OpenTelemetry Protocol (**OTLP**).

In this lesson, you will master distributed tracing with W3C TraceContext, configure Spring Boot with Micrometer Tracing and OTel exporters, deploy an OpenTelemetry Collector pipeline, and correlate traces with application logs.

---

## 1. OpenTelemetry Distributed Architecture

``` mermaid
flowchart TD
    subgraph SpringServices["Spring Boot Microservice Fleet"]
        OrderService["Order Service<br/><i>(Micrometer Tracing + OTel Bridge)</i>"]
        PaymentService["Payment Service<br/><i>(Micrometer Tracing + OTel Bridge)</i>"]
        InventoryService["Inventory Service<br/><i>(Micrometer Tracing + OTel Bridge)</i>"]
        
        OrderService -->|HTTP Call + W3C traceparent header| PaymentService
        PaymentService -->|Kafka Message + W3C Context| InventoryService
    end

    subgraph OTelCollector["OpenTelemetry Collector Pipeline"]
        Receiver["OTLP Receiver (gRPC :4317 / HTTP :4318)"]
        Processor["Processors: Batch, Memory Limiter, Redaction"]
        Exporter["Exporters (OTLP / Vendor Bridges)"]
        
        Receiver --> Processor --> Exporter
    end

    subgraph Backends["Observability & APM Backends"]
        Jaeger["Jaeger / Tempo (Traces)"]
        Prometheus["Prometheus (Metrics)"]
        Loki["Grafana Loki (Logs)"]
        VendorAPM["Datadog / Honeycomb / Dynatrace"]
        
        Exporter --> Jaeger & Prometheus & Loki & VendorAPM
    end

    SpringServices -->|Export OTLP Spans & Metrics| Receiver
```

---

## 2. Distributed Tracing Concepts & W3C TraceContext

A **Trace** represents the complete journey of a request across all microservices, composed of individual units of work called **Spans**:

``` mermaid
flowchart TD
    subgraph TraceRoot["Trace ID: 4bf92f3577b34da6a3ce929d0e0e4736"]
        Span1["Span 1 (Root): OrderService POST /api/v1/orders [150ms]"]
        Span2["Span 2: Database INSERT into orders table [25ms]"]
        Span3["Span 3: PaymentService POST /api/v1/payments [95ms]"]
        Span4["Span 4: Stripe External API Call [80ms]"]
        
        Span1 --> Span2
        Span1 --> Span3
        Span3 --> Span4
    end
```

### Context Propagation (W3C Header Standard)
When `OrderService` makes an HTTP request to `PaymentService`, Micrometer Tracing automatically injects the standard W3C HTTP header:

```http
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
              │  └──────────────┬────────────────┘ └───────┬──────┘ └─┬┘
           Version          Trace ID                    Parent Span ID  Flags (01=Sampled)
```

---

## 3. Configuring Spring Boot with OpenTelemetry & OTLP

Add the OpenTelemetry bridge and OTLP exporter to your build:

### Maven Dependencies (`pom.xml`)
```xml
<!-- 1. Micrometer Tracing Bridge to OpenTelemetry -->
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-otel</artifactId>
</dependency>

<!-- 2. OTLP Exporter to stream spans to OpenTelemetry Collector -->
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-exporter-otlp</artifactId>
</dependency>
```

### `application.yml`
```yaml
management:
  tracing:
    sampling:
      probability: 1.0 # 100% trace sampling in staging; use 0.1 (10%) in high-volume production
  otlp:
    tracing:
      endpoint: http://otel-collector:4317 # OTLP gRPC listener
      timeout: 10s
```

---

## 4. Correlating Traces with Structured Application Logs

Micrometer Tracing automatically enriches your SLF4J / Logback **Mapped Diagnostic Context (MDC)** with active `traceId` and `spanId`:

### `logback-spring.xml`
```xml
<configuration>
    <appender name="JSON_CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder class="net.logstash.logback.encoder.LoggingEventCompositeJsonEncoder">
            <providers>
                <timestamp/>
                <logLevel/>
                <message/>
                <mdc/> <!-- Injects traceId, spanId, and application into every JSON log entry! -->
            </providers>
        </encoder>
    </appender>
</configuration>
```

Now, clicking any log line in Grafana Loki or Elasticsearch lets you jump directly to the exact distributed trace in Jaeger/Tempo with one click!

---

## 5. OpenTelemetry Collector Configuration (`otel-collector-config.yml`)

The OTel Collector decouples applications from specific storage backends:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 1s
    send_batch_size: 256
  memory_limiter:
    check_interval: 1s
    limit_percentage: 75
    spike_limit_percentage: 20

exporters:
  otlp/tempo:
    endpoint: tempo:4317
    tls:
      insecure: true
  prometheus:
    endpoint: 0.0.0.0:8889

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [otlp/tempo]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
```

---

## 6. Spring Boot 3 vs Spring Boot 4: OTel Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Micrometer Tracing 1.2)"]
        Bridges["micrometer-tracing-bridge-otel Wrapper"]
        SeparateExporters["Separate OTLP Exporters for Traces vs Metrics"]
        MdcManual["MDC Trace Injection via Logback Pattern"]
    end

    subgraph SB4["Spring Boot 4.x (Native OpenTelemetry)"]
        NativeOtelSdk["First-Class Spring OTel Starter (No Bridge Layer)"]
        UnifiedOtlpExport["Unified OTLP Signal Exporter (Traces + Metrics + Logs)"]
        NativeLogbackMdc["Zero-Config Automatic OTel Log Appenders"]
    end

    SB3 ==>|Native OTel Engine & Unified OTLP Transport| SB4
```

### Key Differences & Configuration Comparison

| OTel Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **SDK Architecture** | Required Micrometer Tracing API abstraction over OTel SDK. | **Native OTel API**: Direct first-class support for `io.opentelemetry.api.trace.Tracer`. |
| **Signal Export** | Traces used OTLP; metrics used Prometheus `/actuator/prometheus`. | **Unified OTLP Push Pipeline**: Streams Traces, Metrics, and Logs over a single OTLP gRPC channel. |
| **Log Appenders** | Required Logstash logback encoder for MDC trace injection. | **Native OTel Logback Appender**: Auto-emits W3C compliant OpenTelemetry log records. |

---

## 7. Primary Sources & Further Reading

- [OpenTelemetry Official Documentation](https://opentelemetry.io/docs/) — Specification, Data Model, and Collector configuration.
- [Micrometer Tracing Reference Manual](https://micrometer.io/docs/tracing) — Spans, Baggage, and Observation API.
- [W3C Trace Context Specification](https://www.w3.org/TR/trace-context/) — Standard header definitions (`traceparent`, `tracestate`).

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the primary operational advantage of sending telemetry to an OpenTelemetry Collector rather than directly to an APM vendor?"
    **Answer**: The OTel Collector decouples the application from backend storage; switching APM vendors (e.g. from Datadog to Grafana Tempo) only requires updating a collector YAML configuration without touching application code or re-deploying services.

??? question "Question 2: What information is encoded inside the W3C `traceparent` header?"
    **Answer**: The protocol version (e.g. `00`), the 16-byte distributed Trace ID, the 8-byte Parent Span ID, and 8-bit trace options/flags (e.g. `01` for sampled).

??? question "Question 3: How does injecting Trace IDs into application logs solve the problem of debugging distributed outages?"
    **Answer**: It allows engineers to search for a specific error log and instantly retrieve every log line and span across all involved microservices that participated in that exact request.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0046: Grafana Dashboards (RED & USE)**](0046-grafana-dashboards-red-and-use-metrics.md) | [**All Lessons**](index.md) | [➡️ **0048: Unit Testing with JUnit 5 & AssertJ**](0048-unit-testing-junit-5-assertj.md) |

🎉 **Congratulations on completing Module 10: Vendor-Neutral Observability!**
