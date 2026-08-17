---
icon: lucide/bug
---

# Troubleshooting Actuator Security Exposure & ThreadLocal MDC Leaks

Actuator endpoints and MDC logging are vital for production observability. However, misconfigured Actuator exposure creates catastrophic data breach vulnerabilities, and un-cleared MDC context keys lead to **silent cross-tenant logging pollution** across reused thread pools.

This debugging playbook provides diagnostic tests, root-cause analyses, and production remediation patterns.

---

## 1. Issue 1: Public Exposure of Sensitive Actuator Endpoints

### The Symptom
Security scans or penetration testers report that `/actuator/env`, `/actuator/beans`, or `/actuator/heapdump` are accessible over public HTTP endpoints without authentication, leaking credentials and database connection strings.

### Root Cause
Using wildcard exposure `management.endpoints.web.exposure.include="*"` without Spring Security protection:

```yaml
# ❌ DANGEROUS WILDCARD EXPOSURE
management:
  endpoints:
    web:
      exposure:
        include: "*" # Exposes /env, /heapdump, /threaddump, /mappings publicly!
```

### The Fix
1. **Explicitly allowlist only non-sensitive endpoints**:
```yaml
# ✅ SECURE MINIMAL ALLOWLIST
management:
  endpoints:
    web:
      exposure:
        include: ["health", "info", "metrics", "prometheus"]
```

2. **Isolate Actuator to an Internal Management Port**:
```yaml
# ✅ Binds actuator to internal port not exposed to external Ingress/LB
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

## 2. Issue 2: MDC ThreadLocal Pollution & Context Crosstalk

### The Symptom
In Kibana, log records for **Customer A** intermittently contain the `userId` or `traceId` of **Customer B**, corrupting audit trails and privacy compliance.

### Root Cause Architecture

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
    Note over Thread: Request completes.<br/>💥 MDC.clear() was FORGOTTEN!
    Thread-->>Alice: 200 OK
    
    Note over Thread: Thread #3 returns to Tomcat thread pool with dirty MDC!

    Bob->>Thread: GET /profile (User: Bob)
    Note over Thread: Handler doesn't set MDC userId.
    Thread->>Log: log.info("Loading profile")
    Note over Log: 💥 LOGS DIRTY CONTEXT:<br/>{userId: "Alice", message: "Loading profile"}<br/>(Cross-tenant leakage!)
    Thread-->>Bob: 200 OK
```

---

### The Fix: Mandatory `try-finally` MDC Sanitization

Every filter or async task that mutates MDC **must** clear it inside a `finally` block:

```java
// ✅ BULLETPROOF MDC WRAPPER
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
            // 🛡️ Guarantees thread cleanliness even if exceptions occur!
            MDC.clear();
        }
    }
}
```

### Propagating MDC into `@Async` Thread Pools
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

## 🧭 Navigation & Diagnostic Playbooks

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Transaction Rollback & Proxy Pitfalls**](transaction-rollback-and-proxy-pitfalls.md) | [**All Debugging Guides**](index.md) | [➡️ **Security Filter Chain & JWT Pitfalls**](security-filter-chain-and-jwt-pitfalls.md) |
