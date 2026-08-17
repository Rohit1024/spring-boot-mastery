---
icon: lucide/activity
---

# Prometheus, Grafana & OpenTelemetry Cheatsheet

A rapid reference guide for Micrometer Prometheus configuration, PromQL query formulas, Grafana RED/USE dashboard panels, and OpenTelemetry OTLP tracing.

---

## 1. Spring Boot Prometheus & Actuator Setup

### Dependencies (`pom.xml`):
```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

### Configuration (`application.yml`):
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus,metrics
  metrics:
    distribution:
      percentiles-histogram:
        http.server.requests: true
```

---

## 2. Essential PromQL Query Reference

| Metric Purpose | PromQL Formula |
| :--- | :--- |
| **Request Rate (RPS)** | `sum(rate(http_server_requests_seconds_count{application="$app"}[1m])) by (status)` |
| **5xx Error Rate (%)** | `(sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))) * 100` |
| **P99 Latency (s)** | `histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket{application="$app"}[5m])) by (le))` |
| **Heap Memory (%)** | `(sum(jvm_memory_used_bytes{area="heap"}) / sum(jvm_memory_max_bytes{area="heap"})) * 100` |
| **Hikari Saturation** | `hikaricp_connections_pending{application="$app"}` |

---

## 3. OpenTelemetry (OTel) Configuration

### Dependencies (`pom.xml`):
```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-tracing-bridge-otel</artifactId>
</dependency>
<dependency>
    <groupId>io.opentelemetry</groupId>
    <artifactId>opentelemetry-exporter-otlp</artifactId>
</dependency>
```

### Configuration (`application.yml`):
```yaml
management:
  tracing:
    sampling:
      probability: 1.0 # 100% trace sampling
  otlp:
    tracing:
      endpoint: http://otel-collector:4317
```

### W3C TraceContext Header Format:
```text
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

---

## 4. OTel Collector Pipeline Architecture (`otel-collector.yml`)

```yaml
receivers:
  otlp:
    protocols:
      grpc: { endpoint: "0.0.0.0:4317" }

processors:
  batch: { timeout: 1s, send_batch_size: 256 }
  memory_limiter: { limit_percentage: 75 }

exporters:
  otlp/tempo: { endpoint: "tempo:4317", tls: { insecure: true } }
  prometheus: { endpoint: "0.0.0.0:8889" }

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

## 🧭 Navigation & Cheatsheet Index

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Spring Modulith & Virtual Threads Cheatsheet**](spring-modulith-and-virtual-threads.md) | [**All Cheatsheets**](index.md) | [➡️ **Enterprise Testing & Testcontainers Cheatsheet**](enterprise-testing-and-testcontainers.md) |
