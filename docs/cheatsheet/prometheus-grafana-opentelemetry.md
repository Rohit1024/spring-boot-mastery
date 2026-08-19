---
icon: lucide/activity
---

# Prometheus, Grafana, and OpenTelemetry cheatsheet

Reference for Micrometer Prometheus configuration, PromQL query formulas, Grafana RED and USE dashboard panels, and OpenTelemetry OTLP tracing.

---

## 1. Spring Boot Prometheus and Actuator setup

### Dependencies (`pom.xml`)
```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

### Configuration (`application.yml`)
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

## 2. Essential PromQL query reference

| Metric purpose | PromQL formula |
| :--- | :--- |
| **Request rate (RPS)** | `sum(rate(http_server_requests_seconds_count{application="$app"}[1m])) by (status)` |
| **5xx error rate (%)** | `(sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))) * 100` |
| **P99 latency (s)** | `histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket{application="$app"}[5m])) by (le))` |
| **Heap memory (%)** | `(sum(jvm_memory_used_bytes{area="heap"}) / sum(jvm_memory_max_bytes{area="heap"})) * 100` |
| **Hikari saturation** | `hikaricp_connections_pending{application="$app"}` |

---

## 3. OpenTelemetry configuration

### Dependencies (`pom.xml`)
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

### Configuration (`application.yml`)
```yaml
management:
  tracing:
    sampling:
      probability: 1.0 # 100% trace sampling
  otlp:
    tracing:
      endpoint: http://otel-collector:4317
```

### W3C TraceContext header format
```text
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
```

---

## 4. OpenTelemetry collector pipeline architecture (`otel-collector.yml`)

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

## Navigation and cheatsheet index

| Previous | Cheatsheet index | Next |
| :--- | :---: | ---: |
| [**Spring Modulith and virtual threads cheatsheet**](spring-modulith-and-virtual-threads.md) | [**All cheatsheets**](index.md) | [**Enterprise testing and Testcontainers cheatsheet**](enterprise-testing-and-testcontainers.md) |
