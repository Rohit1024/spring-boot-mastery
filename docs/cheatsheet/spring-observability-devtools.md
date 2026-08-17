---
icon: lucide/gauge
---

# Spring Observability, Actuator & Logging Cheatsheet

A rapid-reference guide for Spring Boot Actuator endpoints, Micrometer metrics, OpenAPI 3 annotations, Logback structured JSON configurations, and MDC correlation filters.

---

## 1. Spring Boot Actuator Production Configuration

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
        enabled: true # /actuator/health/liveness & /actuator/health/readiness
  metrics:
    tags:
      application: ${spring.application.name:order-service}
      environment: ${SPRING_PROFILES_ACTIVE:production}
```

### Essential Actuator Endpoints

| Endpoint | Method | Purpose |
| :--- | :---: | :--- |
| `/actuator/health` | `GET` | Overall application health status (`UP`, `DOWN`, `OUT_OF_SERVICE`). |
| `/actuator/health/liveness` | `GET` | Kubernetes Liveness probe (restarts pod on internal JVM crash). |
| `/actuator/health/readiness` | `GET` | Kubernetes Readiness probe (routes traffic when DB/deps are ready). |
| `/actuator/metrics` | `GET` | Lists all registered JVM and custom business metric names. |
| `/actuator/metrics/{name}` | `GET` | Retrieves detailed dimensional metric measurements. |
| `/actuator/prometheus` | `GET` | Formats metrics for automated Prometheus scraper scraping. |
| `/actuator/loggers/{name}` | `GET / POST` | Reads or dynamically overrides runtime log levels without restarting. |

---

## 2. Micrometer Custom Metrics Snippets

```java
@Service
public class MetricService {
    private final Counter orderCounter;
    private final Timer paymentTimer;
    private final AtomicInteger activeUsers;

    public MetricService(MeterRegistry registry) {
        // 1. Counter (Monotonically increasing)
        this.orderCounter = Counter.builder("orders.placed")
                .tag("channel", "mobile")
                .register(registry);

        // 2. Timer (Latency distribution & percentiles)
        this.paymentTimer = Timer.builder("payment.latency")
                .publishPercentiles(0.5, 0.95, 0.99)
                .register(registry);

        // 3. Gauge (Fluctuating value)
        this.activeUsers = registry.gauge("users.active.gauge", new AtomicInteger(0));
    }
}
```

---

## 3. OpenAPI 3 / SpringDoc Quick Reference

```java
@RestController
@RequestMapping("/api/v1/orders")
@Tag(name = "Orders", description = "Order management API")
@SecurityRequirement(name = "BearerAuth")
public class OrderController {

    @Operation(summary = "Place order", description = "Validates and creates customer purchase order")
    @ApiResponses({
        @ApiResponse(responseCode = "201", description = "Created",
            content = @Content(schema = @Schema(implementation = OrderResponse.class))),
        @ApiResponse(responseCode = "400", description = "Bad Request",
            content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
    })
    @PostMapping
    public ResponseEntity<OrderResponse> createOrder(@Valid @RequestBody CreateOrderRequest request) { ... }
}
```

---

## 4. MDC Correlation Filter Pattern

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class CorrelationIdFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        try {
            String traceId = Optional.ofNullable(req.getHeader("X-Correlation-ID"))
                    .orElse(UUID.randomUUID().toString().substring(0, 8));
            MDC.put("traceId", traceId);
            res.setHeader("X-Correlation-ID", traceId);
            chain.doFilter(req, res);
        } finally {
            MDC.clear(); // Always clear in finally block!
        }
    }
}
```

---

## 5. Runtime Log Level Modification via cURL

```bash
# Set package logging to DEBUG in production:
curl -X POST http://localhost:8080/actuator/loggers/com.example.demo \
     -H "Content-Type: application/json" \
     -d '{"configuredLevel": "DEBUG"}'

# Reset back to INFO:
curl -X POST http://localhost:8080/actuator/loggers/com.example.demo \
     -H "Content-Type: application/json" \
     -d '{"configuredLevel": "INFO"}'
```

---

## 🧭 Navigation & Cheatsheet Index

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Spring Data JPA & Hibernate Cheatsheet**](spring-data-jpa-hibernate.md) | [**All Cheatsheets**](index.md) | [➡️ **Spring Security 6 & JWT Cheatsheet**](spring-security-6-jwt-oauth2.md) |
