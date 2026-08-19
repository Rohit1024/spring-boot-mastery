---
icon: lucide/bug
---

# Troubleshooting Actuator security exposure and ThreadLocal MDC leaks

Misconfigured Actuator exposure leaks credentials and internal state, while uncleared MDC keys cause cross-tenant log pollution across reused thread pools. Here is how to diagnose and fix both.

---

## 1. Issue 1: Public exposure of sensitive Actuator endpoints

### Symptoms
Security scans or penetration testers report that `/actuator/env`, `/actuator/beans`, or `/actuator/heapdump` are accessible over public HTTP endpoints without authentication, leaking credentials and database connection strings.

### Root cause
Using wildcard exposure `management.endpoints.web.exposure.include="*"` without Spring Security protection:

```yaml
# Wildcard exposure
management:
  endpoints:
    web:
      exposure:
        include: "*" # Exposes /env, /heapdump, /threaddump, /mappings publicly.
```

### The fix
1. **Allowlist only required endpoints**:
```yaml
management:
  endpoints:
    web:
      exposure:
        include: ["health", "info", "metrics", "prometheus"]
```

2. **Isolate Actuator to an internal management port**:
```yaml
management:
  server:
    port: 8081 # Main app on 8080, Actuator on private 8081
```

3. **Secure with Spring Security**:
```java
@Bean
public SecurityFilterChain actuatorSecurityFilterChain(HttpSecurity http) throws Exception {
    return http
        .securityMatcher(EndpointRequest.toAnyEndpoint())
        .authorizeHttpRequests(auth -> auth
            .requestMatchers(EndpointRequest.to(HealthEndpoint.class, InfoEndpoint.class)).permitAll()
            .anyRequest().hasRole("ADMIN")
        )
        .httpBasic(Customizer.withDefaults())
        .build();
}
```

---

## 2. Issue 2: MDC ThreadLocal pollution and context crosstalk

### Symptoms
In Kibana, log records for Customer A intermittently contain the `userId` or `traceId` of Customer B, corrupting audit trails.

### Root cause architecture

``` mermaid
sequenceDiagram
    autonumber
    actor Alice as Alice (Request 1)
    actor Bob as Bob (Request 2)
    participant Thread as Tomcat Worker Thread #3
    participant MDC as ThreadLocal MDC Map
    participant Log as Log Output

    Alice->>Thread: POST /checkout (User: Alice)
    Thread->>MDC: MDC.put("userId", "Alice")
    Thread->>Log: log.info("Payment placed") -> {userId: "Alice"}
    Note over Thread: Request completes.<br/>MDC.clear() was forgotten.
    Thread-->>Alice: 200 OK
    
    Note over Thread: Thread #3 returns to Tomcat thread pool with dirty MDC.

    Bob->>Thread: GET /profile (User: Bob)
    Note over Thread: Handler doesn't set MDC userId.
    Thread->>Log: log.info("Loading profile")
    Note over Log: Logs dirty context:<br/>{userId: "Alice", message: "Loading profile"}<br/>(Cross-tenant leakage)
    Thread-->>Bob: 200 OK
```

---

### The fix: Mandatory `try-finally` MDC cleanup

Every filter or asynchronous task that mutates MDC must clear it inside a `finally` block:

```java
@Component
public class CorrelationIdFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                     HttpServletResponse response,
                                     FilterChain filterChain) throws ServletException, IOException {
        try {
            String correlationId = Optional.ofNullable(request.getHeader("X-Correlation-ID"))
                    .orElseGet(() -> UUID.randomUUID().toString());
            
            MDC.put("traceId", correlationId);
            response.setHeader("X-Correlation-ID", correlationId);

            filterChain.doFilter(request, response);
        } finally {
            // Guarantees thread cleanliness even if exceptions occur.
            MDC.clear();
        }
    }
}
```

### Propagating MDC into `@Async` thread pools
Standard `ThreadLocal` variables do not cross into `@Async` worker threads. Use a `TaskDecorator`:

```java
public class MdcTaskDecorator implements TaskDecorator {
    @Override
    public Runnable decorate(Runnable runnable) {
        Map<String, String> contextMap = MDC.getCopyOfContextMap();
        return () -> {
            try {
                if (contextMap != null) {
                    MDC.setContextMap(contextMap);
                }
                runnable.run();
            } finally {
                MDC.clear();
            }
        };
    }
}
```

---

## Navigation and debugging index

| Previous | Debugging index | Next |
| :--- | :---: | ---: |
| [**Transaction rollback and proxy pitfalls**](transaction-rollback-and-proxy-pitfalls.md) | [**All debugging guides**](index.md) | [**Security filter chain and JWT pitfalls**](security-filter-chain-and-jwt-pitfalls.md) |
