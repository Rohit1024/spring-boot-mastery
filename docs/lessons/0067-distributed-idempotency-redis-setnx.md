---
icon: lucide/repeat
---

# 0067: Distributed idempotency: Duplicate prevention with Redis SETNX

In high-concurrency distributed systems, duplicate requests are guaranteed to occur:
1. **Network Retries**: A client submits a payment, the server charges the card, but a network blip drops the response. The client's HTTP library retries automatically, risking a double charge.
2. **User Impatience**: A mobile user double-taps the "Submit Order" button on a laggy connection.
3. **Kafka At-Least-Once Delivery**: Consumer group rebalances or transient broker timeouts cause duplicate event delivery.

An **Idempotent** API guarantees that executing an operation multiple times produces the exact same system state and outcome as executing it once: $f(f(x)) = f(x)$.

In this lesson, you will master distributed idempotency key design, atomic Redis `SETNX` (`setIfAbsent`) locking, creating a reusable Spring AOP `@Idempotent` annotation, and handling in-flight race conditions.

---

## 1. Distributed idempotency flow with Redis `SETNX`

``` mermaid
flowchart TD
    subgraph ClientRequest["Incoming Client HTTP Call"]
        ClientReq["POST /api/v1/payments (Header: 'Idempotency-Key: 8f9b-1234')"]
    end

    subgraph SpringApp["Spring Boot Application Layer"]
        IdempotencyAspect["IdempotencyAspect (AOP Around Advice)"]
        PaymentService["PaymentService (Charge Card $100)"]
    end

    subgraph RedisStore["Redis Distributed Store"]
        RedisLock["Redis Key: 'idempotency:key:8f9b-1234'"]
    end

    ClientReq --> IdempotencyAspect
    IdempotencyAspect -->|1. Atomic SETNX with 120s TTL| RedisLock

    RedisLock -.->|2a. Lock Acquired: Key was absent| IdempotencyAspect
    IdempotencyAspect -->|3a. Execute Business Logic| PaymentService
    PaymentService -->|4a. Cache Success Response in Redis| RedisLock
    IdempotencyAspect -->|5a. Return HTTP 200 OK| ClientReq

    RedisLock -.->|2b. Key Exists: State is 'PROCESSING'| IdempotencyAspect
    IdempotencyAspect -.->|3b. Return HTTP 409 Conflict In-Flight| ClientReq

    RedisLock -.->|2c. Key Exists: State has 'CACHED_RESPONSE'| IdempotencyAspect
    IdempotencyAspect -.->|3c. Return Cached HTTP 200 Response Directly| ClientReq
```

---

## 2. The anatomy of an idempotency key

An **Idempotency Key** is a unique client-generated token (typically a UUIDv4) attached to mutating HTTP requests:

```http
POST /api/v1/payments HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOi...
Idempotency-Key: 9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d
Content-Type: application/json

{
    "orderId": "ORD-5541",
    "amount": 100.00,
    "currency": "USD"
}
```

---

## 3. Custom `@Idempotent` annotation aspect

### 1. Custom annotation

```java
package com.example.annotation;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Idempotent {
    /**
     * Time-to-live for the idempotency key in seconds
     */
    long ttlSeconds() default 120;

    /**
     * Header name carrying the client token
     */
    String headerName() default "Idempotency-Key";
}
```

---

### 2. Idempotency aspect with atomic Redis `setIfAbsent`

```java
package com.example.aspect;

import com.example.annotation.Idempotent;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletRequest;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.Duration;

@Slf4j
@Aspect
@Component
@RequiredArgsConstructor
public class DistributedIdempotencyAspect {

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;

    @Around("@annotation(idempotentConfig)")
    public Object enforceIdempotency(ProceedingJoinPoint joinPoint, Idempotent idempotentConfig) throws Throwable {
        ServletRequestAttributes attrs = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
        if (attrs == null) {
            return joinPoint.proceed();
        }

        HttpServletRequest request = attrs.getRequest();
        String idempotencyKey = request.getHeader(idempotentConfig.headerName());

        // If client did not provide idempotency key, proceed normally
        if (idempotencyKey == null || idempotencyKey.isBlank()) {
            return joinPoint.proceed();
        }

        String redisKey = "idempotency:key:" + idempotencyKey;
        Duration ttl = Duration.ofSeconds(idempotentConfig.ttlSeconds());

        // 🔒 Atomic SET key "PROCESSING" NX EX <ttl>
        Boolean lockAcquired = redisTemplate.opsForValue().setIfAbsent(redisKey, "PROCESSING", ttl);

        if (Boolean.TRUE.equals(lockAcquired)) {
            // First execution: proceed with business logic
            try {
                Object result = joinPoint.proceed();
                
                // Cache the successful return value for future duplicate calls
                String serializedResult = objectMapper.writeValueAsString(result);
                redisTemplate.opsForValue().set(redisKey, serializedResult, ttl);
                return result;
            } catch (Throwable ex) {
                // Remove lock on failure so the client can retry safely
                redisTemplate.delete(redisKey);
                throw ex;
            }
        } else {
            // Key already exists in Redis
            String cachedValue = redisTemplate.opsForValue().get(redisKey);

            if ("PROCESSING".equals(cachedValue)) {
                log.warn("Concurrent duplicate request in-flight for key: {}", idempotencyKey);
                return ResponseEntity.status(HttpStatus.CONFLICT)
                        .body("A request with this Idempotency-Key is currently processing. Please wait.");
            }

            log.info("Returning cached idempotent response for key: {}", idempotencyKey);
            // Deserialize and return previously computed response
            return objectMapper.readValue(cachedValue, Object.class);
        }
    }
}
```

---

## 4. Applying idempotency to payment controllers

```java
package com.example.controller;

import com.example.annotation.Idempotent;
import com.example.dto.PaymentRequest;
import com.example.dto.PaymentResponse;
import com.example.service.PaymentService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/payments")
@RequiredArgsConstructor
public class PaymentController {

    private final PaymentService paymentService;

    @PostMapping
    @Idempotent(ttlSeconds = 300) // Protected for 5 minutes
    public ResponseEntity<PaymentResponse> processPayment(@RequestBody PaymentRequest request) {
        PaymentResponse response = paymentService.charge(request);
        return ResponseEntity.ok(response);
    }
}
```

---

## 5. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Idempotency Abstraction** | Custom AOP aspect using `StringRedisTemplate.setIfAbsent()`. | Native `@Idempotent` method filters integrated directly into Spring MVC. |
| **Response Caching** | Manual Jackson JSON string serialization in Redis. | Zero-copy binary response stream memoization in Redis Valkey cluster. |
| **Distributed Locks** | Redis single-instance `SETNX` or Redisson distributed locks. | Multi-datacenter consensus locks with lease renewal heartbeats. |

---

## 6. Primary sources and further reading

- [IETF Draft: The Idempotency-Key HTTP Header Field](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/).
- [Stripe API Reference: Idempotent Requests](https://stripe.com/docs/api/idempotent_requests), Industry gold standard for payment idempotency.
- [Redis Distributed Locks with Redis `SETNX`](https://redis.io/docs/manual/patterns/distributed-locks/).

---

## 7. Knowledge check and practice

??? question "Question 1: What does it mean for an API operation to be idempotent?"
    **Answer**: It means that making multiple identical requests has the exact same side effects and produces the same outcome as making a single request.

??? question "Question 2: How does Redis `SETNX` (`setIfAbsent`) guarantee atomic lock acquisition?"
    **Answer**: It sets the key only if it does not already exist in Redis in a single atomic step, preventing race conditions between concurrent requests.

??? question "Question 3: Why should an idempotency lock be deleted if the business logic throws an unhandled exception?"
    **Answer**: To allow the client to retry the failed operation immediately rather than being blocked by the in-flight lock until the TTL expires.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0066: High-Scale Reads: CQRS Architecture**](0066-high-scale-reads-cqrs-architecture.md) | [**All Lessons**](index.md) | [ **0068: CAP Theorem in Action: Consistency vs Availability**](0068-cap-theorem-consistency-availability-payments.md) |

🎉 **Lesson 0067 completed! Proceed to Lesson 0068 to master trade-offs in distributed systems with the CAP Theorem.**
