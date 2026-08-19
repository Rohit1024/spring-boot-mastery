---
icon: lucide/file-code
---

# Microservices, Kubernetes, and cloud CI/CD cheatsheet

Production reference card for Spring Cloud (OpenFeign, Gateway, Config Server, Eureka), Resilience4j fault tolerance, distributed patterns (Saga, outbox, idempotency), Kubernetes workloads, and AWS CI/CD.

---

## 1. Spring Cloud OpenFeign declarative client

```java
@FeignClient(name = "payment-service", path = "/api/v1/payments", configuration = FeignConfig.class)
public interface PaymentClient {
    @PostMapping("/charge")
    PaymentResponse charge(@RequestBody PaymentRequest request);
}

// Bearer token propagation interceptor
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

## 2. Spring Cloud Gateway YAML configuration

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

## 3. Resilience4j fault tolerance reference

| Annotation | Key configuration | Purpose |
| :--- | :--- | :--- |
| `@CircuitBreaker` | `failure-rate-threshold: 50`, `wait-duration-in-open-state: 10s` | Trips to OPEN on 50% failures; returns immediate fallback. |
| `@Retry` | `max-attempts: 3`, `wait-duration: 500ms`, `exponential-backoff: true` | Retries on transient network exceptions with backoff. |
| `@Bulkhead` | `max-concurrent-calls: 15`, `max-wait-duration: 20ms` | Isolates concurrent executions to prevent thread starvation. |
| `@TimeLimiter` | `timeout-duration: 2s` | Aborts long-hanging asynchronous calls. |

---

## 4. Distributed transaction and reliability patterns

### Transactional outbox worker (`SKIP LOCKED`)
```sql
SELECT * FROM outbox_events WHERE status = 'PENDING' ORDER BY created_at ASC LIMIT 50 FOR UPDATE SKIP LOCKED;
```

### Distributed idempotency key with Redis `SETNX`
```java
Boolean acquired = redisTemplate.opsForValue().setIfAbsent("idempotency:" + key, "PROCESSING", Duration.ofMinutes(5));
if (Boolean.TRUE.equals(acquired)) {
    // Proceed with business logic...
} else {
    // Return HTTP 409 Conflict or cached response
}
```

---

## 5. Kubernetes production manifests

### Zero-downtime deployment and probes
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

## 6. AWS CodeBuild `buildspec.yml` phase matrix

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

## Navigation and cheatsheet index

| Previous | Cheatsheet index | Next |
| :--- | :---: | ---: |
| [**Redis caching and Kafka cheatsheet**](redis-caching-and-kafka-messaging.md) | [**All cheatsheets**](index.md) | [**Reactive WebFlux and Spring AI cheatsheet**](reactive-webflux-and-spring-ai.md) |
