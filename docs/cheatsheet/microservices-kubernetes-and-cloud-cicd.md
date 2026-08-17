---
icon: lucide/file-code
---

# Microservices, Kubernetes & Cloud CI/CD Cheatsheet

A production reference card for Spring Cloud (OpenFeign, Gateway, Config Server, Eureka), Resilience4j fault tolerance, distributed patterns (SAGA, Outbox, Idempotency), Kubernetes workloads, and AWS CI/CD.

---

## 1. Spring Cloud OpenFeign Declarative Client

```java
@FeignClient(name = "payment-service", path = "/api/v1/payments", configuration = FeignConfig.class)
public interface PaymentClient {
    @PostMapping("/charge")
    PaymentResponse charge(@RequestBody PaymentRequest request);
}

// Bearer Token Propagation Interceptor
@Bean
public RequestInterceptor bearerTokenInterceptor() {
    return template -> {
        ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (attrs != null) {
            String token = attrs.getRequest().getHeader("Authorization");
            if (token != null) template.header("Authorization", token);
        }
    };
}
```

---

## 2. Spring Cloud Gateway YAML Configuration

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: order-service-route
          uri: lb://ORDER-SERVICE
          predicates:
            - Path=/api/v1/orders/**
          filters:
            - RewritePath=/api/v1/orders/(?<segment>.*), /api/orders/${segment}
            - AddResponseHeader=X-Gateway, SpringCloudGateway
```

---

## 3. Resilience4j Fault Tolerance Cheat Sheet

| Annotation | Key Configuration | Purpose |
| :--- | :--- | :--- |
| **`@CircuitBreaker`** | `failure-rate-threshold: 50`, `wait-duration-in-open-state: 10s` | Trips to OPEN on 50% failures; returns immediate fallback. |
| **`@Retry`** | `max-attempts: 3`, `wait-duration: 500ms`, `exponential-backoff: true` | Retries on transient network exceptions with backoff. |
| **`@Bulkhead`** | `max-concurrent-calls: 15`, `max-wait-duration: 20ms` | Isolates concurrent executions to prevent thread starvation. |
| **`@TimeLimiter`** | `timeout-duration: 2s` | Aborts long-hanging asynchronous calls. |

---

## 4. Distributed Transaction & Reliability Patterns

### Transactional Outbox Worker (`SKIP LOCKED`)
```sql
SELECT * FROM outbox_events WHERE status = 'PENDING' ORDER BY created_at ASC LIMIT 50 FOR UPDATE SKIP LOCKED;
```

### Distributed Idempotency Key with Redis `SETNX`
```java
Boolean acquired = redisTemplate.opsForValue().setIfAbsent("idempotency:" + key, "PROCESSING", Duration.ofMinutes(5));
if (Boolean.TRUE.equals(acquired)) {
    // Proceed with business logic...
} else {
    // Return HTTP 409 Conflict or cached response
}
```

---

## 5. Kubernetes Production Manifests

### Zero-Downtime Deployment & Probes
```yaml
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
        - name: app
          image: registry.io/app:1.0.0
          resources:
            requests: { memory: "512Mi", cpu: "250m" }
            limits: { memory: "1024Mi", cpu: "1000m" }
          livenessProbe:
            httpGet: { path: /actuator/health/liveness, port: 8080 }
            initialDelaySeconds: 30
          readinessProbe:
            httpGet: { path: /actuator/health/readiness, port: 8080 }
            initialDelaySeconds: 15
```

---

## 6. AWS CodeBuild `buildspec.yml` Phase Matrix

```yaml
version: 0.2
phases:
  install:
    runtime-versions: { java: corretto21 }
  pre_build:
    commands:
      - mvn clean test -B
      - aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI
  build:
    commands:
      - docker build -t $ECR_URI:latest .
  post_build:
    commands:
      - docker push $ECR_URI:latest
      - printf '[{"name":"app","imageUri":"%s"}]' "$ECR_URI:latest" > imagedefinitions.json
artifacts:
  files: [ imagedefinitions.json, target/*.jar ]
```

---

## 🧭 Navigation & Cheatsheet Index

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Redis Caching & Kafka Cheatsheet**](redis-caching-and-kafka-messaging.md) | [**All Cheatsheets**](index.md) | [➡️ **Reactive WebFlux & Spring AI Cheatsheet**](reactive-webflux-and-spring-ai.md) |
