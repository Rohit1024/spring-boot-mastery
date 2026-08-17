---
icon: lucide/gauge
---

# 0056: Rate Limiting Algorithms in Redis: Token Bucket & Sliding Window

Without robust rate limiting, microservices are vulnerable to noisy neighbors, denial-of-service (DoS) bursts, cascading database overloads, and runaway client scripts.

Because Spring Boot applications scale horizontally across dozens of stateless instances, in-memory local rate limiters fail to enforce global limits. **Redis** serves as the distributed source of truth for rate limiting, providing atomic execution via **Lua scripts** with sub-millisecond overhead.

In this lesson, you will master the 4 core rate limiting algorithms (Fixed Window, Sliding Window Log, Sliding Window Counter, and Token Bucket), author atomic Redis Lua scripts, and build a Spring Boot rate-limiting interceptor that returns RFC-compliant `429 Too Many Requests` responses.

---

## 1. Rate Limiting Request Flow & Algorithms

``` mermaid
flowchart TD
    subgraph Client["Client Tier"]
        ClientReq["HTTP Request (e.g. GET /api/v1/orders, IP / API Key)"]
    end

    subgraph SpringApp["Spring Boot Application Layer"]
        RateLimitInterceptor["RateLimitInterceptor (HandlerInterceptor)"]
        Controller["OrderController"]
    end

    subgraph RedisTier["Redis (Atomic Lua Script Execution)"]
        LuaEngine["Redis Lua Script Engine (Atomic EVALSHA)"]
        TokenBucketKey["Key: 'ratelimit:token_bucket:client_101' (Hash: tokens, last_refill)"]
        SlidingWindowKey["Key: 'ratelimit:sliding_window:client_101' (Sorted Set: ZSet)"]
    end

    ClientReq --> RateLimitInterceptor
    RateLimitInterceptor -->|1. Execute Lua Script atomically| LuaEngine
    LuaEngine --> TokenBucketKey
    LuaEngine --> SlidingWindowKey

    LuaEngine -.->|2a. Allowed Tokens available| RateLimitInterceptor
    RateLimitInterceptor -->|3a. Forward Request| Controller

    LuaEngine -.->|2b. Blocked Limit Exceeded| RateLimitInterceptor
    RateLimitInterceptor -.->|3b. Return HTTP 429 and Retry-After| ClientReq
```

---

## 2. Algorithm Comparison & Trade-Off Matrix

| Algorithm | Mechanism | Advantages | Drawbacks / Failure Modes |
| :--- | :--- | :--- | :--- |
| **Fixed Window Counter** | Increments a counter keyed to a discrete time bucket (e.g. `rate:user1:12:01`). Reset on bucket expiry. | Simple, minimal Redis RAM (1 integer key per window). | **Boundary Burst Problem**: Up to 2x limit can pass during window transitions (e.g. 100 requests at 11:59:59 and 100 at 12:00:01). |
| **Sliding Window Log** | Stores each request timestamp in a Redis Sorted Set (`ZSet`). Purges timestamps older than `now - window`. | 100% mathematically exact; zero boundary spikes. | **High Memory Consumption**: Stores a member for every single request; memory explodes under high traffic. |
| **Sliding Window Counter** | Blends the count of the previous window and current window based on current percentage elapsed. | Smooths out boundary bursts; low memory (2 counter keys). | Approximation (assumes uniform distribution in previous window). |
| **Token Bucket** | Tokens refill at a steady rate up to `capacity`. Each request consumes 1 token. | Allows controlled bursts up to capacity while enforcing average rate. Industry standard for APIs. | Requires state tracking (current tokens + last timestamp). |

---

## 3. Production Token Bucket Lua Script (`token_bucket.lua`)

In high-concurrency environments, executing multiple sequential Redis commands (`GET`, check, `SET`) introduces race conditions. Redis **Lua scripts** execute atomically on the Redis single-threaded engine, eliminating the need for distributed locks:

```lua
-- KEYS[1]: Rate limit key (e.g., "ratelimit:token_bucket:user_123")
-- ARGV[1]: Max bucket capacity (e.g., 10)
-- ARGV[2]: Refill rate per second (e.g., 2)
-- ARGV[3]: Current timestamp in seconds (e.g., 1718000000)
-- ARGV[4]: Requested tokens (e.g., 1)

local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

-- Retrieve current bucket state
local data = redis.call("HMGET", key, "tokens", "last_refill")
local current_tokens = tonumber(data[1])
local last_refill = tonumber(data[2])

if current_tokens == nil then
    -- Initialize bucket for new client
    current_tokens = capacity
    last_refill = now
else
    -- Calculate refilled tokens since last request
    local elapsed = math.max(0, now - last_refill)
    local refilled = elapsed * refill_rate
    current_tokens = math.min(capacity, current_tokens + refilled)
    last_refill = now
end

-- Check if sufficient tokens exist
if current_tokens >= requested then
    current_tokens = current_tokens - requested
    redis.call("HMSET", key, "tokens", current_tokens, "last_refill", last_refill)
    -- Set TTL to auto-expire idle keys (capacity / refill_rate * 2)
    redis.call("EXPIRE", key, math.ceil(capacity / refill_rate) * 2)
    return {1, math.floor(current_tokens)} -- [1 = Allowed, remaining_tokens]
else
    redis.call("HMSET", key, "tokens", current_tokens, "last_refill", last_refill)
    return {0, math.floor(current_tokens)} -- [0 = Rejected, remaining_tokens]
end
```

---

## 4. Spring Boot Token Bucket Service

```java
package com.example.service;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.Collections;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class RateLimiterService {

    private final StringRedisTemplate redisTemplate;
    private DefaultRedisScript<List> tokenBucketScript;

    @PostConstruct
    public void init() {
        tokenBucketScript = new DefaultRedisScript<>();
        tokenBucketScript.setLocation(new ClassPathResource("scripts/token_bucket.lua"));
        tokenBucketScript.setResultType(List.class);
    }

    public record RateLimitResult(boolean isAllowed, long remainingTokens) {}

    public RateLimitResult isAllowed(String clientId, int capacity, int refillRatePerSec) {
        String key = "ratelimit:token_bucket:" + clientId;
        long currentTimestamp = Instant.now().getEpochSecond();

        List<?> result = redisTemplate.execute(
                tokenBucketScript,
                Collections.singletonList(key),
                String.valueOf(capacity),
                String.valueOf(refillRatePerSec),
                String.valueOf(currentTimestamp),
                "1"
        );

        if (result != null && !result.isEmpty()) {
            Long allowed = (Long) result.get(0);
            Long remaining = (Long) result.get(1);
            return new RateLimitResult(allowed == 1L, remaining);
        }

        // Fail-open policy on Redis scripting error
        return new RateLimitResult(true, capacity);
    }
}
```

---

## 5. Spring MVC Interceptor & RFC 6585 Headers

```java
package com.example.interceptor;

import com.example.service.RateLimiterService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
@RequiredArgsConstructor
public class RateLimitInterceptor implements HandlerInterceptor {

    private final RateLimiterService rateLimiterService;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // Resolve client identity (API Key, JWT Subject, or Client IP)
        String apiKey = request.getHeader("X-API-KEY");
        String clientId = (apiKey != null && !apiKey.isBlank()) ? apiKey : request.getRemoteAddr();

        // 10 max burst capacity, refilling 2 tokens per second
        RateLimiterService.RateLimitResult result = rateLimiterService.isAllowed(clientId, 10, 2);

        // Standard RFC Rate Limiting Headers
        response.setHeader("X-RateLimit-Limit", "10");
        response.setHeader("X-RateLimit-Remaining", String.valueOf(result.remainingTokens()));

        if (!result.isAllowed()) {
            response.setStatus(HttpStatus.TOO_MANY_REQUESTS.value()); // HTTP 429
            response.setHeader("Retry-After", "2"); // Suggest retry in 2 seconds
            response.setContentType("application/json");
            response.getWriter().write("""
                {
                    "status": 429,
                    "error": "Too Many Requests",
                    "message": "Rate limit exceeded. Please retry after 2 seconds."
                }
            """);
            return false;
        }

        return true;
    }
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Lua Script Caching** | Spring Data Redis sends `EVAL` with SHA fallback via Lettuce driver. | Native automated `EVALSHA` bytecode caching with zero redundant script transmissions. |
| **Gateway Rate Limiting** | Spring Cloud Gateway uses built-in `RedisRateLimiter` with Token Bucket. | Unified reactive and servlet rate limiting filters with dynamic SpEL quota resolvers. |
| **Redis Engine Support** | Redis 7.x multi-key commands and cluster hash tags. | Full compatibility with Redis 8.x and Valkey open-source engine clustering. |

---

## 7. Primary Sources & Further Reading

- [Redis Programmability & Lua Scripting](https://redis.io/docs/interact/programmability/eval-intro/) — Atomic script execution, `EVAL`, and `EVALSHA`.
- [RFC 6585: Additional HTTP Status Codes (429 Too Many Requests)](https://datatracker.ietf.org/doc/html/rfc6585#section-4).
- [IETF Draft: RateLimit Header Fields for HTTP](https://datatracker.ietf.org/doc/draft-ietf-httpapi-ratelimit-headers/).

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the primary drawback of the Fixed Window Counter rate limiting algorithm?"
    **Answer**: The boundary burst problem, where up to twice the allowable limit of requests can hit the service across the border of two adjacent windows.

??? question "Question 2: Why are Redis Lua scripts preferred over client-side read-modify-write loops for rate limiting?"
    **Answer**: Lua scripts execute atomically inside Redis's single-threaded command processor, preventing concurrent race conditions without costly distributed locking.

??? question "Question 3: Which HTTP status code and response header must be returned when a rate limit is exceeded?"
    **Answer**: HTTP `429 Too Many Requests` along with the `Retry-After` header indicating how many seconds the client should wait before retrying.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0055: Kafka Producer & Consumer with Spring Kafka & DLQ**](0055-kafka-producer-consumer-spring-dlq.md) | [**All Lessons**](index.md) | [➡️ **0057: Monolith vs Microservices: System Design Principles**](0057-monolith-vs-microservices-system-design.md) |

🎉 **Congratulations on completing Module 12: High-Performance Caching & Messaging Systems!**
