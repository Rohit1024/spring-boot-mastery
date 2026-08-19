---
icon: lucide/shield-alert
---

# 0063: Fault tolerance with Resilience4j: Circuit Breaker, Retry, and Bulkhead

In a distributed microservice architecture, remote network calls will inevitably fail or experience extreme latency. If a downstream Payment Service begins hanging for 30 seconds per request, upstream services quickly exhaust their Tomcat worker thread pools waiting for socket responses, triggering a catastrophic **cascading outage** across the entire cluster.

**Resilience4j** is a lightweight, fault-tolerance library designed for Java functional programming. It provides Circuit Breakers, Retries, Rate Limiters, and Bulkheads to isolate downstream failures and preserve system stability.

In this lesson, you will master Circuit Breaker state machines, configuring sliding window thresholds, crafting robust fallback handlers, and preventing resource starvation with Bulkheads.

---

## 1. Circuit breaker state machine architecture

``` mermaid
flowchart TD
    subgraph CircuitStates["Resilience4j State Machine"]
        Closed["CLOSED State (Normal Operations: Calls permitted to remote service)"]
        Open["OPEN State (Tripped: Calls fail immediately with CallNotPermittedException)"]
        HalfOpen["HALF_OPEN State (Trial: Test configured number of probe calls)"]
    end

    Closed -->|Failure Rate or Slow Calls exceed threshold e.g. 50%| Open
    Open -->|Wait duration expires e.g. 10 seconds| HalfOpen
    HalfOpen -->|Probe calls succeed| Closed
    HalfOpen -->|Probe calls fail| Open
```

---

## 2. Maven dependencies (`pomxml`)

```xml
<dependency>
    <groupId>io.github.resilience4j</groupId>
    <artifactId>resilience4j-spring-boot3</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aop</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

---

## 3. Production `application.yml` configuration

Configure sliding windows, timeout limits, and failure thresholds:

```yaml
resilience4j:
  circuitbreaker:
    instances:
      paymentService:
        # Evaluate last 20 calls (COUNT_BASED) or last 10 seconds (TIME_BASED)
        sliding-window-type: COUNT_BASED
        sliding-window-size: 20
        minimum-number-of-calls: 10
        # Trip to OPEN if 50% of calls fail or throw exceptions
        failure-rate-threshold: 50
        # Trip to OPEN if 40% of calls take longer than 2 seconds (Slow Call Detection)
        slow-call-rate-threshold: 40
        slow-call-duration-threshold: 2000ms
        # Duration to remain in OPEN state before testing with probe calls
        wait-duration-in-open-state: 10000ms
        # Number of probe calls permitted in HALF_OPEN state
        permitted-number-of-calls-in-half-open-state: 4
        automatic-transition-from-open-to-half-open-enabled: true
        # Record only server errors; ignore client 4xx validation errors
        ignore-exceptions:
          - com.example.exception.InvalidRequestException

  retry:
    instances:
      paymentService:
        max-attempts: 3
        wait-duration: 500ms
        enable-exponential-backoff: true
        exponential-backoff-multiplier: 2
        retry-exceptions:
          - org.springframework.web.client.ResourceAccessException
          - java.util.concurrent.TimeoutException

  bulkhead:
    instances:
      paymentService:
        # Limit concurrent calls to prevent exhausting thread pool
        max-concurrent-calls: 15
        max-wait-duration: 20ms
```

---

## 4. Implementing resilient services fallbacks

> [!IMPORTANT]
> **Fallback Method Signature Rule**: The fallback method **must** reside in the same class, have the exact same return type and parameter list as the original method, plus a trailing `Throwable` (or specific exception) parameter.

```java
package com.example.service;

import com.example.client.PaymentClient;
import com.example.dto.PaymentRequest;
import com.example.dto.PaymentResponse;
import io.github.resilience4j.bulkhead.annotation.Bulkhead;
import io.github.resilience4j.circuitbreaker.CallNotPermittedException;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.retry.annotation.Retry;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class PaymentProcessingService {

    private final PaymentClient paymentClient;

    /**
     * Stacked Resilience Decorators:
     * 1. Bulkhead limits concurrency.
     * 2. CircuitBreaker protects against outages.
     * 3. Retry handles momentary network hiccups.
     */
    @Bulkhead(name = "paymentService", fallbackMethod = "bulkheadFallback")
    @CircuitBreaker(name = "paymentService", fallbackMethod = "processPaymentFallback")
    @Retry(name = "paymentService")
    public PaymentResponse executePayment(PaymentRequest request) {
        log.info("Executing remote payment call for order: {}", request.orderId());
        return paymentClient.processPayment(request);
    }

    /**
     * Fallback method executed when Circuit is OPEN or payment call fails
     */
    public PaymentResponse processPaymentFallback(PaymentRequest request, Throwable ex) {
        log.warn("Payment fallback triggered for order {}. Reason: {}", request.orderId(), ex.getMessage());
        
        if (ex instanceof CallNotPermittedException) {
            log.error("Circuit breaker is OPEN. Fast-failing payment to prevent thread exhaustion.");
        }
        
        // Return graceful degraded response or enqueue for asynchronous reconciliation
        return new PaymentResponse(
                request.orderId(),
                "PENDING_OFFLINE_RECONCILIATION",
                "Payment service temporarily degraded. Order queued for offline processing."
        );
    }

    /**
     * Bulkhead fallback executed when concurrent call limit (15) is saturated
     */
    public PaymentResponse bulkheadFallback(PaymentRequest request, Throwable ex) {
        log.warn("Bulkhead concurrency saturated for order {}", request.orderId());
        return new PaymentResponse(request.orderId(), "RATE_LIMITED", "System busy. Please retry shortly.");
    }
}
```

---

## 5. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Resilience Engine** | Resilience4j Spring Boot 3 starter using Spring AOP proxies. | Native non-AOP method wrappers with zero reflection overhead. |
| **Virtual Threads Integration** | Semaphore bulkheads preferred over thread-pool bulkheads to avoid pinning carrier threads. | Native Virtual Thread concurrency limiters and non-blocking timeout carriers. |
| **Metrics & Events** | Actuator exposes `/actuator/circuitbreakers` and Prometheus state metrics. | OTel semantic conventions for circuit breaker transitions and drop spans. |

---

## 6. Primary sources and further reading

- [Resilience4j Official Documentation](https://resilience4j.readme.io/), CircuitBreaker, Retry, Bulkhead, and RateLimiter.
- [Release It! Second Edition, Michael Nygard](https://pragprog.com/titles/mnee2/release-it-second-edition/), Foundational patterns for stability and capacity.
- [Spring Cloud Circuit Breaker Documentation](https://docs.spring.io/spring-cloud-circuitbreaker/reference/).

---

## 7. Knowledge check and practice

??? question "Question 1: What happens when a Circuit Breaker enters the `OPEN` state?"
    **Answer**: It immediately rejects all incoming calls by throwing a `CallNotPermittedException` (or invoking the fallback) without making any network calls to the downstream service.

??? question "Question 2: What is the purpose of the `HALF_OPEN` state in Resilience4j?"
    **Answer**: It allows a small, configurable number of probe requests through to test if the downstream service has recovered before switching back to `CLOSED` or reopening to `OPEN`.

??? question "Question 3: How does a Bulkhead protect microservices from thread starvation?"
    **Answer**: It limits the maximum number of concurrent executions allocated to a specific downstream service, preventing a slow service from consuming all available application threads.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0062: Distributed Tracing with Micrometer & Zipkin**](0062-distributed-tracing-micrometer-zipkin.md) | [**All Lessons**](index.md) | [ **0064: SAGA Pattern with Kafka Choreography**](0064-distributed-transactions-saga-pattern.md) |

🎉 **Lesson 0063 completed! Proceed to Lesson 0064 to master distributed multi-service transactions with the SAGA Pattern.**
