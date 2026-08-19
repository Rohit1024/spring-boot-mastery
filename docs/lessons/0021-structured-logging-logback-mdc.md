---
icon: lucide/terminal
---

# 0021: Structured application logging with SLF4J, Logback, and MDC

In high-scale distributed architectures processing millions of concurrent requests, traditional unstructured plaintext log files (e.g. `2026-08-17 10:00:00 INFO User logged in`) are nearly impossible to query, parse, or aggregate efficiently.

Modern observability demands **Structured JSON Logging** and **Distributed Context Propagation**. In this lesson, you will configure **Logback** to produce structured JSON events with `logstash-logback-encoder`, implement **Mapped Diagnostic Context (MDC)** in a Servlet Filter to inject correlation IDs, and dynamically alter log levels in production at runtime via Spring Boot Actuator.

---

## 1. Plaintext logs vs structured JSON logs

``` mermaid
flowchart TD
    subgraph Legacy["❌ Legacy Plaintext Logs"]
        Plain["2026-08-17 14:32:01.102 INFO 4920 --- [nio-8080-exec-1] c.e.OrderService : Processing order 99201 for user usr_44"]
    end

    subgraph Structured["✅ Modern Structured JSON Log Event"]
        JSON["{<br/>  '@timestamp': '2026-08-17T14:32:01.102Z',<br/>  'level': 'INFO',<br/>  'service': 'order-service',<br/>  'traceId': 'c7b91a2e',<br/>  'userId': 'usr_44',<br/>  'orderId': '99201',<br/>  'message': 'Order processed successfully'<br/>}"]
    end

    Legacy ~~~ Structured
```

### Why structured JSON wins
- **Zero Regex Parsing**: Elasticsearch, Datadog, and CloudWatch index JSON keys natively into fast inverted index fields.
- **Dimensional Filtering**: Instantly run queries like `service: order-service AND userId: usr_44 AND level: ERROR`.
- **Contextual Correlation**: Every log emitted within a request automatically carries the same `traceId` and `clientIp`.

---

## 2. Setting up `logstash-logback-encoder`

Add the encoder to your `pom.xml`:

```xml
<dependency>
    <groupId>net.logstash.logback</groupId>
    <artifactId>logstash-logback-encoder</artifactId>
    <version>8.0</version>
</dependency>
```

### Production `logback-spring.xml`

Create `src/main/resources/logback-spring.xml` to output structured JSON in production while retaining human-friendly console output in local development:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>

    <springProfile name="dev">
        <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
            <encoder>
                <pattern>%d{HH:mm:ss.SSS} [%thread] %highlight(%-5level) %cyan(%logger{36}) [%X{traceId}] - %msg%n</pattern>
            </encoder>
        </appender>
        <root level="INFO">
            <appender-ref ref="CONSOLE"/>
        </root>
    </springProfile>

    <springProfile name="prod,stage">
        <appender name="JSON_CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
            <encoder class="net.logstash.logback.encoder.LogstashEncoder">
                <customFields>{"service":"order-service","environment":"production"}</customFields>
                <includeMdcKeyName>traceId</includeMdcKeyName>
                <includeMdcKeyName>userId</includeMdcKeyName>
                <includeMdcKeyName>clientIp</includeMdcKeyName>
            </encoder>
        </appender>
        <root level="INFO">
            <appender-ref ref="JSON_CONSOLE"/>
        </root>
    </springProfile>

</configuration>
```

---

## 3. Mapped diagnostic context (MDC) architecture

**MDC (Mapped Diagnostic Context)** is an SLF4J feature backed by Java's `ThreadLocal`. It allows you to set key-value context variables at the beginning of an HTTP request that are automatically included in **every log statement** executed on that thread.

``` mermaid
sequenceDiagram
    autonumber
    actor Client as External Client
    participant Filter as CorrelationIdFilter (OncePerRequestFilter)
    participant MDC as SLF4J MDC (ThreadLocal Map)
    participant Service as OrderService
    participant Log as Logback JSON Appender

    Client->>Filter: HTTP POST /orders (Header: X-Correlation-ID: c7b91a2e)
    Filter->>MDC: MDC.put("traceId", "c7b91a2e")
    Filter->>MDC: MDC.put("clientIp", "192.168.1.50")
    
    Filter->>Service: processOrder()
    Service->>Log: log.info("Validating order inventory")
    Note over Log: Logback reads MDC ThreadLocal.<br/>Appends "traceId":"c7b91a2e" to JSON!
    
    Service->>Log: log.info("Payment captured successfully")
    
    Service-->>Filter: Returns OrderResponse
    Filter->>MDC: MDC.clear() (Prevents ThreadLocal leaks)
    Filter-->>Client: HTTP 201 Created (Header: X-Correlation-ID: c7b91a2e)
```

---

## 4. Implementing the correlation id servlet filter

```java
package com.example.demo.filter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE) // Executes before Spring Security & Controllers
public class CorrelationIdFilter extends OncePerRequestFilter {

    public static final String CORRELATION_ID_HEADER = "X-Correlation-ID";
    public static final String MDC_TRACE_ID_KEY = "traceId";
    public static final String MDC_CLIENT_IP_KEY = "clientIp";

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        try {
            // 1. Extract existing correlation ID or generate a new UUID
            String correlationId = request.getHeader(CORRELATION_ID_HEADER);
            if (correlationId == null || correlationId.isBlank()) {
                correlationId = UUID.randomUUID().toString().replace("-", "").substring(0, 16);
            }

            // 2. Populate MDC ThreadLocal
            MDC.put(MDC_TRACE_ID_KEY, correlationId);
            MDC.put(MDC_CLIENT_IP_KEY, request.getRemoteAddr());

            // 3. Return correlation ID in HTTP response headers for client tracking
            response.setHeader(CORRELATION_ID_HEADER, correlationId);

            // 4. Continue filter chain execution
            filterChain.doFilter(request, response);

        } finally {
            // ⚠️ CRITICAL: Tomcat reuses thread pool workers!
            // Failing to clear MDC will leak previous request IDs into subsequent requests!
            MDC.clear();
        }
    }
}
```

---

## 5. Dynamic log level switching via actuator

In production, you often need to temporarily enable `DEBUG` logging on a specific package to diagnose an active incident without restarting the container.

### 1. View current log levels
```bash
curl -X GET http://localhost:8080/actuator/loggers/com.example.demo
```
**Response**:
```json
{
  "configuredLevel": "INFO",
  "effectiveLevel": "INFO"
}
```

### 2. Dynamically switch to `DEBUG`
```bash
curl -X POST http://localhost:8080/actuator/loggers/com.example.demo \
     -H "Content-Type: application/json" \
     -d '{"configuredLevel": "DEBUG"}'
```
*Instantly, all loggers under `com.example.demo` begin emitting `DEBUG` logs in real time!*

---

## 6. Spring Boot 3 vs Spring Boot 4: Logging context evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        ThreadLocalMDC["ThreadLocal-backed SLF4J MDC"]
        CustomJsonEncoder["logstash-logback-encoder / ecs-logging"]
        ManualMdcWrap["Manual TaskDecorator for Async Threads"]
    end

    subgraph SB4["Spring Boot 4.x"]
        OTelBaggage["OpenTelemetry Baggage & Scoped Values"]
        NativeJsonLogger["Built-in Structured JSON Logging Starters"]
        AutoLoomProp["Auto-Loom Context Propagation"]
    end

    SB3 ==>|Telemetry Convergence| SB4
```

### Key differences and configuration comparison

| Logging Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Contextual MDC Storage** | `ThreadLocal` storage; prone to leaks or carrier thread pollution under Virtual Threads without careful `finally` cleanup. | **Java 21+ Scoped Values & OTel Baggage**: Immutable, leak-proof context propagation natively preserved across Loom forks. |
| **JSON Logging Setup** | Required third-party `logstash-logback-encoder` or `ecs-logging-logback` in `pom.xml`. | **Native Structured Logging**: Configurable directly via `logging.structured.format.console=json` out-of-the-box. |
| **Trace Context Standard** | Wired through Micrometer Tracing bridges (Brave / OpenTelemetry). | **Pure W3C Distributed TraceContext**: Zero-bridge native header propagation. |

---

## 7. Primary sources and further reading

- [SLF4J Mapped Diagnostic Context (MDC) Manual](https://www.slf4j.org/manual.html#mdc), Official guide on ThreadLocal context propagation.
- [Logstash Logback Encoder Documentation](https://github.com/logfellow/logstash-logback-encoder), Custom JSON fields, masking, and formatting.
- [Spring Boot Actuator: Loggers Endpoint](https://docs.spring.io/spring-boot/reference/actuator/endpoints.html#actuator.endpoints.loggers), Runtime log level adjustments.

---

## 8. Knowledge check and practice

??? question "Question 1: Why is clearing MDC via `MDC.clear()` inside a `finally` block mandatory in Servlet environments?"
    **Answer**: Web servers like Tomcat use thread pools; failing to clear MDC causes residual context variables (e.g. `traceId`) to bleed into unrelated subsequent requests executed by the reused thread.

??? question "Question 2: What is the primary advantage of Structured JSON logging over traditional plaintext logs in log aggregation pipelines?"
    **Answer**: JSON logs are parsed directly by aggregation systems without brittle regular expressions, enabling fast dimensional indexing and filtering by fields like `userId` or `traceId`.

??? question "Question 3: How can you change a logger's level in production without restarting the Spring Boot JVM?"
    **Answer**: By issuing an HTTP `POST` request to `/actuator/loggers/{logger.name}` with a payload specifying `{"configuredLevel": "DEBUG"}`.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0020: OpenAPI 3 & Swagger UI Documentation**](0020-openapi-3-and-swagger-ui-documentation.md) | [**All Lessons**](index.md) | [ **0022: Centralized Logging with ELK Stack**](0022-centralized-logging-elk-stack.md) |
