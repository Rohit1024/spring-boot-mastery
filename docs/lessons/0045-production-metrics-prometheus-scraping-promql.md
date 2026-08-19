---
icon: lucide/activity
---

# 0045: Production metrics with Prometheus: Scraping, PromQL, and alert rules

In high-availability enterprise environments, guessing application health based on CPU load alone is fatal. Engineers need real-time dimensional metrics to monitor HTTP throughput, P99 latency percentiles, database connection saturation, and JVM garbage collection overhead.

**Prometheus** is the Cloud Native Computing Foundation (CNCF) industry-standard time-series monitoring system. Paired with Spring Boot Actuator and **Micrometer**, it provides dimensional metrics collected via pull-based scraping and queried using **PromQL**.

In this lesson, you will master configuring the Prometheus Actuator endpoint, writing high-performance PromQL queries, and configuring automated alerting rules for production SLA violations.

---

## 1. Prometheus metrics collection architecture

``` mermaid
flowchart TD
    subgraph SpringApp["Spring Boot Application Fleet"]
        Actuator["Spring Boot Actuator"]
        Micrometer["Micrometer Prometheus MeterRegistry"]
        Endpoint["/actuator/prometheus (Text/OpenMetrics Exposition)"]
        
        Actuator --> Micrometer --> Endpoint
    end

    subgraph PrometheusServer["Prometheus Time-Series Engine"]
        Scraper["Prometheus Pull Scraper (e.g. Every 15s)"]
        TSDB[("Prometheus TSDB (Time-Series Database)")]
        PromQL["PromQL Query Engine"]
        RuleEngine["Alerting Rule Evaluator"]
        
        Scraper --> TSDB
        TSDB --> PromQL & RuleEngine
    end

    subgraph Alerting["Alert Dispatch Pipeline"]
        Alertmanager["Prometheus Alertmanager"]
        PagerDuty["PagerDuty / Slack / Opsgenie"]
        
        RuleEngine -->|Fires Alert| Alertmanager --> PagerDuty
    end

    Scraper -->|HTTP GET Scrape| Endpoint
```

---

## 2. Enabling Prometheus endpoint in Spring Boot

Add the Micrometer Prometheus registry to your build:

### Maven dependency (`pomxml`)
```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

### `application.yml`
```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus,metrics
  endpoint:
    prometheus:
      enabled: true
  metrics:
    tags:
      application: ${spring.application.name}
      environment: production
    distribution:
      percentiles-histogram:
        http.server.requests: true # Enables detailed P50, P90, P95, P99 latency buckets
      sla:
        http.server.requests: 50ms, 100ms, 250ms, 500ms, 1000ms
```

Accessing `http://localhost:8080/actuator/prometheus` yields dimensional metrics in the OpenMetrics format:
```text
# HELP http_server_requests_seconds Duration of HTTP server requests
# TYPE http_server_requests_seconds summary
http_server_requests_seconds_count{application="order-service",environment="production",exception="none",method="GET",outcome="SUCCESS",status="200",uri="/api/v1/orders/{id}"} 4218
http_server_requests_seconds_sum{application="order-service",environment="production",exception="none",method="GET",outcome="SUCCESS",status="200",uri="/api/v1/orders/{id}"} 128.45
```

---

## 3. Essential PromQL formulas for Spring Boot

PromQL (Prometheus Query Language) transforms raw time-series data into real-time operational insights:

### 1. Http request throughput (requests per second)
```promql
sum(rate(http_server_requests_seconds_count{application="order-service"}[1m])) by (uri, method, status)
```

### 2. Http 5xx error rate percentage
```promql
(sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) 
 / 
 sum(rate(http_server_requests_seconds_count[5m]))) * 100
```

### 3. P99 request latency (sla monitoring)
```promql
histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket{application="order-service"}[5m])) by (le, uri))
```

### 4. JVM heap memory utilization percentage
```promql
(sum(jvm_memory_used_bytes{area="heap"}) 
 / 
 sum(jvm_memory_max_bytes{area="heap"})) * 100
```

### 5. Hikaricp database connection pool saturation
```promql
(hikaricp_connections_active 
 / 
 hikaricp_connections_max) * 100
```

---

## 4. Production Prometheus alerting rules (`alertsyml`)

Prometheus evaluates alerting rules continuously against TSDB metrics:

```yaml
groups:
  - name: spring_boot_production_alerts
    rules:
      # Alert 1: High 5xx Server Error Rate
      - alert: HighHttp5xxErrorRate
        expr: (sum(rate(http_server_requests_seconds_count{status=~"5.."}[5m])) / sum(rate(http_server_requests_seconds_count[5m]))) * 100 > 2.0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High HTTP 5xx error rate on {{ $labels.application }}"
          description: "Service is throwing >2% 5xx errors for more than 2 minutes. Current rate: {{ $value }}%."

      # Alert 2: P99 Latency SLA Breach
      - alert: HttpP99LatencyBreach
        expr: histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket[5m])) by (le, application)) > 1.0
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "P99 latency exceeding 1 second on {{ $labels.application }}"
          description: "P99 latency has breached 1.0s SLA for 3 minutes. Current value: {{ $value }}s."

      # Alert 3: HikariCP Connection Pool Exhaustion
      - alert: DatabasePoolExhaustion
        expr: (hikaricp_connections_active / hikaricp_connections_max) * 100 > 85.0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection pool near exhaustion on {{ $labels.application }}"
          description: "HikariCP active connections exceeded 85% for 1 minute."
```

---

## 5. Spring Boot 3 vs Spring Boot 4: Prometheus evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Micrometer 1.12+)"]
        TextExposition["Standard OpenMetrics / Prometheus Text 0.0.4"]
        ClassicMeters["Classic ObservationRegistry & Timers"]
        PlatformGCMeters["Standard JVM G1GC Memory Metrics"]
    end

    subgraph SB4["Spring Boot 4.x (Micrometer 2.0)"]
        OpenMetrics2["Native OpenMetrics 2.0 Binary Protocol Format"]
        NativeOTelBridge["Direct Zero-Overhead Prometheus-to-OTel Bridge"]
        VirtualThreadMeters["Built-in Virtual Thread & Carrier Pool Gauge Metrics"]
    end

    SB3 ==>|OpenMetrics 2.0 & Loom Metric Gauges| SB4
```

### Key differences and configuration comparison

| Metric Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Exposition Format** | Text-based Prometheus format (`text/plain; version=0.0.4`). | **OpenMetrics 2.0 Binary Format**: High-throughput protobuf metric scraping. |
| **Virtual Thread Telemetry** | Required custom gauges to monitor Loom carrier threads. | **Native Loom Metrics**: Auto-exposes `jvm.threads.virtual.pinned` and `jvm.threads.virtual.mounted`. |
| **Exemplars Support** | Supported only with OpenTelemetry tracer integration. | **Native Trace Exemplars**: Automatically links metric spikes directly to trace IDs in Prometheus. |

---

## 6. Primary sources and further reading

- [Prometheus Official Documentation](https://prometheus.io/docs/introduction/overview/), Architecture, scrape configurations, and TSDB internals.
- [Micrometer Prometheus Meter Registry](https://micrometer.io/docs/registry/prometheus), Timer, distribution summary, and SLA percentile configuration.
- [Robust Perception: PromQL Best Practices](https://www.robustperception.io/blog/), Authoritative guide to PromQL query optimization.

---

## 7. Knowledge check and practice

??? question "Question 1: What is the purpose of `management.metrics.distribution.percentiles-histogram.http.server.requests=true` in `application.yml`?"
    **Answer**: It enables generation of latency histogram buckets (`_bucket{le="..."}`), which are strictly required by Prometheus to calculate percentile queries like P95 and P99 via `histogram_quantile()`.

??? question "Question 2: Why should `rate()` always be used instead of raw counter values when calculating request throughput in PromQL?"
    **Answer**: Counters continuously increase and reset to 0 on application restarts; `rate()` computes the per-second rate of increase over a time window and smoothly handles counter resets.

??? question "Question 3: What role does Prometheus Alertmanager play in production monitoring?"
    **Answer**: It deduplicates, groups, and routes active alert firings evaluated by Prometheus to downstream notification channels like PagerDuty, Slack, or webhook handlers.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0044: Java 21 Virtual Threads (Loom)**](0044-java-virtual-threads-project-loom-spring-boot.md) | [**All Lessons**](index.md) | [ **0046: Grafana Dashboards (RED & USE)**](0046-grafana-dashboards-red-and-use-metrics.md) |
