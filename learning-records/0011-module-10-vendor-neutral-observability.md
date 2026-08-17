# Learning Record 0011: Module 10 — Vendor-Neutral Observability Completed

- **Date**: 2026-08-17
- **Module**: Module 10: Vendor-Neutral Observability — Prometheus, Grafana & OpenTelemetry
- **Status**: Completed

## Concepts Mastered

1. **Prometheus & Micrometer Integration**:
   - Prometheus pull-based scraping model over `/actuator/prometheus` in OpenMetrics format.
   - Enabling latency histogram buckets via `management.metrics.distribution.percentiles-histogram.http.server.requests=true`.
   - Core PromQL formulas: `rate()` throughput calculations, 5xx error rate percentages, and `histogram_quantile(0.99, ...)` P99 SLA tracking.
   - Writing Prometheus Alerting Rules (`alert.rules.yml`) and routing via Alertmanager to PagerDuty/Slack.

2. **Enterprise Dashboarding with Grafana**:
   - The RED Method for user-facing services: Rate (RPS), Errors (5xx rate), Duration (P50/P90/P99 latency).
   - The USE Method for internal infrastructure: Utilization (JVM Heap/CPU), Saturation (Hikari pending connections, Carrier thread queues), and Errors (GC pause spikes).
   - Dynamic dashboard templating using Prometheus label variables (`$environment`, `$application`, `$instance`, `$uri`).

3. **OpenTelemetry (OTel) Distributed Tracing**:
   - Overcoming proprietary vendor lock-in with CNCF standard OpenTelemetry Protocol (OTLP).
   - Anatomy of distributed tracing: Traces, Spans, and W3C `traceparent` context header propagation across microservices.
   - OpenTelemetry Collector pipeline configuration: Receivers (OTLP gRPC :4317 / HTTP :4318) -> Processors (batch, memory limiter) -> Exporters (Tempo, Prometheus, Loki).
   - Unified observability correlation: injecting `traceId` and `spanId` into SLF4J MDC logs for 1-click cross-system root-cause navigation.

## Artifacts Produced

- Lessons: `0045`, `0046`, `0047` (with Spring Boot 3 vs 4 comparisons and vertical Mermaid diagrams).
- Cheatsheet: `docs/cheatsheet/prometheus-grafana-opentelemetry.md`.
- Debugging Guide: `docs/debugging/prometheus-scraping-and-opentelemetry-collector-pitfalls.md`.
- Interview Questions: 10 high-signal observability questions in `docs/interview/index.md`.
- Glossary: Added definitions for Prometheus, PromQL, RED Method, USE Method, OpenTelemetry, Span, TraceContext, and OTLP.
