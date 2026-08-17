---
icon: lucide/bug
---

# Troubleshooting Microservices, Circuit Breaker & SAGA Pitfalls

Distributed systems introduce complex failure dynamics: network partitions, cascading timeouts, circuit breaker flapping, ghost service discovery entries, and partial SAGA rollback failures.

This playbook provides root-cause analyses, diagnostic flowcharts, and concrete resolutions for common Spring Cloud, Resilience4j, SAGA, and Kubernetes orchestration pitfalls.

---

## 1. Diagnostic Flow: Microservice Cascades & Failures

``` mermaid
flowchart TD
    Issue["Symptom Detected in Microservices Mesh"]

    subgraph CircuitBreakerBranch["Circuit Breaker & Cascading Latency"]
        CallNotPermitted["CallNotPermittedException / 503 Outage"]
        Check4xx{"Are 4xx client errors tripping the circuit?"}
        FixIgnore4xx["Add 4xx exceptions to ignore-exceptions list"]
        CheckTimeout{"Are slow downstream calls exhausting threads?"}
        FixBulkhead["Tune slowCallDurationThreshold and configure Bulkhead"]
    end

    subgraph EurekaBranch["Service Discovery & Routing"]
        DeadPodRouted["502 Bad Gateway: Traffic routed to terminated Pods"]
        CheckSelfPreserve{"Is Eureka Self-Preservation Mode active?"}
        FixEurekaLease["Reduce leaseRenewal & leaseExpiration durations"]
    end

    subgraph SAGABranch["Distributed Transactions & SAGA"]
        PartialRollback["Data Inconsistency: Payment deducted but Stock not released"]
        CheckCompensation{"Did a compensating transaction fail?"}
        FixCompensate["Implement Outbox retry & Dead Letter Topic reconciliation"]
    end

    Issue --> CallNotPermitted
    Issue --> DeadPodRouted
    Issue --> PartialRollback

    CallNotPermitted --> Check4xx
    Check4xx -->|Yes| FixIgnore4xx
    Check4xx -->|No| CheckTimeout
    CheckTimeout --> FixBulkhead

    DeadPodRouted --> CheckSelfPreserve
    CheckSelfPreserve --> FixEurekaLease

    PartialRollback --> CheckCompensation
    CheckCompensation --> FixCompensate
```

---

## 2. Pitfall 1: Circuit Breaker Tripped by Client 4xx Errors

### Symptom Log
```text
io.github.resilience4j.circuitbreaker.CallNotPermittedException: 
CircuitBreaker 'paymentService' is OPEN and does not permit further calls
```

### Root Cause
Resilience4j records all thrown exceptions as failures by default. When legitimate clients submit invalid payment payloads (e.g. expired credit cards throwing HTTP `400 Bad Request`), the failure rate threshold quickly exceeds 50%, tripping the circuit to `OPEN` and blocking all subsequent valid payments.

### Resolution
Explicitly ignore client validation exceptions in `application.yml`:

```yaml
resilience4j:
  circuitbreaker:
    instances:
      paymentService:
        failure-rate-threshold: 50
        # 🔒 Ignore client validation and business rejections
        ignore-exceptions:
          - com.example.exception.InvalidPaymentPayloadException
          - com.example.exception.CardDeclinedException
        # Record only genuine downstream server/network errors
        record-exceptions:
          - org.springframework.web.client.HttpServerErrorException
          - java.util.concurrent.TimeoutException
          - java.net.ConnectException
```

---

## 3. Pitfall 2: Eureka Routing Traffic to Terminated Pods ("Ghost Instances")

### Symptom Log
```text
org.springframework.web.client.ResourceAccessException: 
I/O error on POST request for "http://10.244.2.85:8080/api/v1/payments": Connect to 10.244.2.85:8080 failed: Connection refused
```

### Root Cause
When a pod terminates, Eureka's default settings can take up to **2–3 minutes** to remove the IP from all client caches:
1. Server lease expiration default: 90 seconds.
2. Eureka server response cache refresh: 30 seconds.
3. Spring Cloud LoadBalancer client cache refresh: 30 seconds.

### Resolution
Tune Eureka heartbeat and cache expiration intervals in `application.yml`:

```yaml
# In Microservice Client:
eureka:
  instance:
    lease-renewal-interval-in-seconds: 5
    lease-expiration-duration-in-seconds: 15

# In Eureka Server:
eureka:
  server:
    response-cache-update-interval-ms: 3000
    eviction-interval-timer-in-ms: 5000
```

---

## 4. Pitfall 3: SAGA Partial Compensation Failure

### Symptom
Customer's credit card was charged $150, but because the shipping service was unreachable, the order was cancelled without issuing a refund.

### Root Cause
The `handleOrderCancelled` compensating listener in Payment Service failed with a database lock error or network timeout and dropped the event because no retry policy or outbox table was configured.

### Resolution
Compensating transactions **must never be dropped**. Wrap compensations inside resilient retry topics with DLQ manual alerting:

```java
// ✅ RESOLUTION: Guaranteed Non-Blocking Compensation Retries
@RetryableTopic(
        attempts = "5",
        backoff = @Backoff(delay = 1000, multiplier = 2.0),
        dltStrategy = DltStrategy.FAIL_ON_ERROR
)
@KafkaListener(topics = "order-events", groupId = "payment-compensation-group")
public void compensatePayment(OrderCancelledEvent event, Acknowledgment ack) {
    paymentService.issueRefund(event.orderId());
    ack.acknowledge();
}
```

---

## 5. Pitfall 4: Kubernetes Readiness Probe Cascading Outage

### Symptom
When PostgreSQL undergoes a 10-second failover, Kubernetes immediately marks all 20 Spring Boot application pods **Unready**, dropping all traffic from the Ingress and causing a 100% platform outage.

### Root Cause
The Kubernetes `readinessProbe` was pointed to `/actuator/health` instead of the dedicated `/actuator/health/readiness` group. By default, `/actuator/health` probes all external dependencies (DB, Redis, Disk). If one backing service hiccups, Kubernetes takes down every pod.

### Resolution
Use dedicated liveness and readiness probe endpoints:

```yaml
# ✅ RESOLUTION: Point K8s probes to isolated Actuator sub-groups
readinessProbe:
  httpGet:
    path: /actuator/health/readiness # Checks only if Spring ApplicationContext is up
    port: 8080
livenessProbe:
  httpGet:
    path: /actuator/health/liveness  # Checks internal JVM liveness
    port: 8080
```

---

## 🧭 Navigation & Diagnostic Playbooks

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Troubleshooting Redis Caching & Kafka Lag**](redis-cache-stampede-and-kafka-consumer-lag.md) | [**All Debugging Guides**](index.md) | [➡️ **Troubleshooting Reactive WebFlux & Spring AI**](reactive-webflux-blocking-and-spring-ai-pitfalls.md) |
