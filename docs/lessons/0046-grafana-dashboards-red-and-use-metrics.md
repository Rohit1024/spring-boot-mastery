---
icon: lucide/layout-dashboard
---

# 0046: Enterprise Dashboarding with Grafana: The RED & USE Metrics Methods

During a production incident, digging through raw logs or staring at 50 disjointed graphs causes cognitive overload and delays mean-time-to-resolution (MTTR). High-performing engineering teams organize their visualization around two battle-tested observability frameworks:

1. **The RED Method** (for Request-Driven Services): **Rate**, **Errors**, and **Duration**.
2. **The USE Method** (for Resources & Infrastructure): **Utilization**, **Saturation**, and **Errors**.

In this lesson, you will master architecting production-grade **Grafana** dashboards for Spring Boot microservices, structuring panels according to RED and USE principles, and implementing dynamic dashboard variables.

---

## 1. Dashboard Architecture: RED vs USE Methods

``` mermaid
flowchart TD
    subgraph REDMethod["1. The RED Method (Request & User-Facing Services)"]
        R1["Rate: How much traffic is the service handling? (req/sec)"]
        E1["Errors: How many requests are failing? (5xx error rate %)"]
        D1["Duration: How long do requests take? (P50, P90, P99 Latency)"]
        
        R1 --> E1 --> D1
    end

    subgraph USEMethod["2. The USE Method (Resources & Internal Infrastructure)"]
        U2["Utilization: How busy is the resource? (JVM Heap %, CPU %)"]
        S2["Saturation: How much extra work is queued? (Hikari Pending, Thread Queue)"]
        E2["Errors: Are resources failing? (GC Pause Spikes, Connection Timeouts)"]
        
        U2 --> S2 --> E2
    end

    subgraph GrafanaView["Grafana Unified Service Dashboard"]
        TopRow["Row 1: High-Level Service RED KPI Stats"]
        MiddleRow["Row 2: Endpoint Latency Breakdown & Heatmaps"]
        BottomRow["Row 3: JVM, HikariCP & Carrier Pool USE Metrics"]
        
        TopRow --> MiddleRow --> BottomRow
    end

    REDMethod & USEMethod --> GrafanaView
```

---

## 2. Implementing the RED Method Panels in Grafana

### Panel 1: Request Rate (Throughput)
- **Visualization**: Time Series (Stacked Area Chart)
- **PromQL Query**:
  ```promql
  sum(rate(http_server_requests_seconds_count{application="$application", environment="$environment"}[1m])) by (status)
  ```

### Panel 2: Error Rate (5xx Failures)
- **Visualization**: Stat / Gauge with Thresholds (Green <0.5%, Yellow >1.0%, Red >2.0%)
- **PromQL Query**:
  ```promql
  (sum(rate(http_server_requests_seconds_count{application="$application", status=~"5.."}[5m])) 
   / 
   sum(rate(http_server_requests_seconds_count{application="$application"}[5m]))) * 100
  ```

### Panel 3: Request Duration (P50 / P95 / P99 Latency)
- **Visualization**: Time Series (Multigraph)
- **PromQL Query**:
  ```promql
  # P99 Latency
  histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket{application="$application"}[5m])) by (le))
  
  # P50 (Median) Latency
  histogram_quantile(0.50, sum(rate(http_server_requests_seconds_bucket{application="$application"}[5m])) by (le))
  ```

---

## 3. Implementing the USE Method Panels (JVM & Database)

### Panel 4: JVM Heap Memory Utilization (USE: Utilization)
```promql
(jvm_memory_used_bytes{application="$application", area="heap"} 
 / 
 jvm_memory_max_bytes{application="$application", area="heap"}) * 100
```

### Panel 5: HikariCP Connection Saturation (USE: Saturation)
Shows threads waiting in line for a database connection:
```promql
hikaricp_connections_pending{application="$application"}
```
*(Any value sustained above 0 indicates database connection starvation).*

### Panel 6: Garbage Collection Pause Duration (USE: Errors / Degradation)
```promql
sum(rate(jvm_gc_pause_seconds_sum{application="$application"}[1m])) by (action, cause)
```

---

## 4. Dynamic Dashboard Templating with Variables

To reuse a single dashboard across all microservices and cloud environments, configure Grafana **Template Variables**:

| Variable Name | Type | Query Source (Prometheus) |
| :--- | :--- | :--- |
| **`$environment`** | Query | `label_values(http_server_requests_seconds_count, environment)` |
| **`$application`** | Query | `label_values(http_server_requests_seconds_count{environment="$environment"}, application)` |
| **`$instance`** | Query | `label_values(http_server_requests_seconds_count{application="$application"}, instance)` |
| **`$uri`** | Query | `label_values(http_server_requests_seconds_count{application="$application"}, uri)` |

---

## 5. Spring Boot 3 vs Spring Boot 4: Dashboarding Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        ManualGrafanaJson["Community Dashboard IDs (e.g. 11378, 12900)"]
        PrometheusDatasource["Standard Prometheus Datasource Queries"]
        StaticThresholds["Static Panel Threshold Configurations"]
    end

    subgraph SB4["Spring Boot 4.x"]
        GrafanaAsCode["Grafana-As-Code (Auto-Generated OpenTelemetry Dashboards)"]
        UnifiedDatasource["Prometheus + Tempo + Loki Correlated Datasources"]
        DynamicSloPanels["Built-in Native Service-Level Objective (SLO) Panels"]
    end

    SB3 ==>|Observability-as-Code & Unified Correlated Telemetry| SB4
```

### Key Differences & Configuration Comparison

| Dashboard Aspect | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Community Dashboard Import** | Imported generic dashboards requiring manual PromQL relabeling. | **Auto-Provisioned OTel Dashboards**: Out-of-the-box standard Spring Framework 7 dashboards. |
| **Data Correlation** | Clicking a latency spike required manually opening Grafana Tempo in another tab. | **Built-in Exemplar Drilldown**: Direct click from Prometheus chart spike to the exact Trace ID in Grafana Tempo. |
| **Virtual Thread Monitoring** | No standard panels for Project Loom carrier pool saturation. | **Dedicated Virtual Thread Panels**: Gauges for carrier queue depth and unmount latency. |

---

## 6. Primary Sources & Further Reading

- [The RED Method by Tom Wilkie](https://grafana.com/blog/2018/08/02/the-red-method-how-to-instrument-your-services/) — Authoritative request monitoring philosophy.
- [The USE Method by Brendan Gregg](https://www.brendangregg.com/usemethod.html) — Resource utilization, saturation, and error diagnostics.
- [Grafana Documentation: Variables and Templating](https://grafana.com/docs/grafana/latest/dashboards/variables/) — Parameterizing dashboards.

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: What three metrics comprise the RED Method, and what type of components is it designed to monitor?"
    **Answer**: Rate (throughput), Errors (failure count/percentage), and Duration (latency distribution); it is designed to monitor request-driven, user-facing services (e.g. REST, GraphQL, gRPC APIs).

??? question "Question 2: What three dimensions comprise the USE Method, and what type of components is it designed to monitor?"
    **Answer**: Utilization (percentage of time/capacity used), Saturation (queued/backlogged work), and Errors; it is designed to monitor internal resources (CPU, JVM memory, database connection pools, thread pools).

??? question "Question 3: Why is tracking P99 latency significantly more informative than tracking average (mean) latency in Grafana?"
    **Answer**: Averages hide extreme latency spikes experienced by a significant subset of users; P99 reveals the worst-case response times that indicate system degradation or SLA violations.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0045: Production Metrics with Prometheus**](0045-production-metrics-prometheus-scraping-promql.md) | [**All Lessons**](index.md) | [➡️ **0047: OpenTelemetry & OTLP Collectors**](0047-opentelemetry-otel-tracing-and-otlp-collectors.md) |
