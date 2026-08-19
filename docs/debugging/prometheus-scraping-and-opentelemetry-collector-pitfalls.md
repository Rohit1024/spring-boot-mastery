---
icon: lucide/bug
---

# Troubleshooting Prometheus scraping and OpenTelemetry collector pitfalls

Production observability depends on continuous telemetry pipelines. When Prometheus cannot scrape endpoints, histogram buckets are omitted, or OpenTelemetry collectors drop spans, engineering teams are left blind during system incidents.

Here are diagnostic workflows and verified solutions for Prometheus and OpenTelemetry telemetry pipeline failures.

---

## 1. Diagnostic decision tree

``` mermaid
flowchart TD
    Start["Observability Pipeline Failure Detected"] --> ErrType{"Identify Failure Category"}

    ErrType -->|Prometheus targets show DOWN or 401/403| ScrapeErr["1. Scrape Endpoint Security Failure"]
    ErrType -->|histogram_quantile returns NaN or empty| HistErr["2. Missing Percentile Buckets"]
    ErrType -->|Spans missing or disconnected in Jaeger / Tempo| SpanErr["3. OTel Collector / Context Drop"]

    ScrapeErr --> FixScrape["Permit /actuator/prometheus in SecurityFilterChain"]
    HistErr --> FixHist["Set percentiles-histogram.http.server.requests=true"]
    SpanErr --> FixSpan["Verify OTLP gRPC endpoint :4317 & W3C header propagation"]
```

---

## 2. Issue 1: Prometheus target shows `DOWN` or 401 Unauthorized

### Symptoms
In Prometheus `http://localhost:9090/targets`, the Spring Boot application shows state `DOWN` with error: `server returned HTTP status 401 Unauthorized` or `403 Forbidden`.

### Root cause
Spring Security's `SecurityFilterChain` blocks unauthenticated HTTP requests to `/actuator/prometheus`.

### Resolution
Permit scraper access to Actuator monitoring endpoints in your `SecurityConfig.java`:

```java
@Bean
public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
    http
        .authorizeHttpRequests(auth -> auth
            // Permit scraper access to prometheus and health
            .requestMatchers("/actuator/prometheus", "/actuator/health/**").permitAll()
            .anyRequest().authenticated()
        );
    return http.build();
}
```

---

## 3. Issue 2: `histogram_quantile()` returns `NaN` or empty in PromQL

### Symptoms
Executing `histogram_quantile(0.99, sum(rate(http_server_requests_seconds_bucket[5m])) by (le))` in Prometheus or Grafana returns no data or `NaN`.

### Root cause
By default, Micrometer does not generate histogram boundary buckets (`_bucket{le="..."}`) for memory optimization. Without buckets, Prometheus cannot compute percentiles.

### Resolution
Enable percentile histograms in `application.yml`:

```yaml
management:
  metrics:
    distribution:
      percentiles-histogram:
        http.server.requests: true # Required for histogram_quantile
      sla:
        http.server.requests: 50ms, 100ms, 250ms, 500ms, 1000ms
```

---

## 4. Issue 3: Distributed traces break across microservice hops

### Symptoms
In Jaeger or Grafana Tempo, traces appear fragmented into individual disconnected single-span traces rather than one continuous multi-service distributed trace tree.

### Diagnostic flowchart

``` mermaid
sequenceDiagram
    autonumber
    participant Order as Order Service (Client)
    participant Rest as RestTemplate / WebClient (Uninstrumented)
    participant Payment as Payment Service (Server)

    Order->>Rest: Makes HTTP POST /payments
    Note over Rest: Missing W3C traceparent header injection.
    Rest->>Payment: HTTP POST /payments (No trace context)
    Payment->>Payment: Generates brand-new trace ID. Trace is severed.
```

### Resolution
Ensure your HTTP clients use Spring auto-configured builders (`RestTemplateBuilder` or `WebClient.Builder`), which automatically register Micrometer Tracing interceptors:

```java
// Manual instantiation bypasses tracing interceptors:
// RestTemplate restTemplate = new RestTemplate();

// Injected builder includes W3C header propagation:
@Bean
public RestTemplate restTemplate(RestTemplateBuilder builder) {
    return builder
            .setConnectTimeout(Duration.ofSeconds(2))
            .setReadTimeout(Duration.ofSeconds(5))
            .build();
}
```

---

## Navigation and debugging index

| Previous | Debugging index | Next |
| :--- | :---: | ---: |
| [**Troubleshooting Spring Modulith and Project Loom**](spring-modulith-and-virtual-thread-pinning-pitfalls.md) | [**All debugging guides**](index.md) | [**Spring Boot testing and Testcontainers debugging**](spring-boot-testing-and-testcontainers-pitfalls.md) |
