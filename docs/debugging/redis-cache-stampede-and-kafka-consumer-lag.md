---
icon: lucide/bug
---

# Troubleshooting Redis Cache Stampede & Kafka Consumer Lag Pitfalls

In high-throughput distributed systems, caching layer failures and message queue pipeline stalls can rapidly cause cascading system-wide outages.

This playbook provides root-cause analyses, diagnostic flows, and battle-tested mitigations for Redis Cache Stampedes, Kafka `CommitFailedException` rebalance storms, and poison pill deserialization deadlocks.

---

## 1. Diagnostic Flow: Cache & Consumer Failures

``` mermaid
flowchart TD
    Issue["Symptom Detected in Production"]
    
    subgraph CachingPath["Cache Outage Path"]
        DBSpike["Database CPU 100% & Connection Pool Exhaustion"]
        CheckTTL{"Did a hot cache key expire?"}
        Stampede["Cache Stampede (Thundering Herd)"]
        Avalanche["Cache Avalanche (Simultaneous TTL Expiration)"]
        FixStampede["Apply @Cacheable(sync = true) or Mutex Lock"]
        FixAvalanche["Add Random TTL Expiration Jitter"]
    end
    
    subgraph KafkaPath["Kafka Consumer Path"]
        LagSpike["High Consumer Lag & CommitFailedException"]
        PollTimeout{"Processing time > max.poll.interval.ms?"}
        PoisonPill{"SerializationException in Log?"}
        RebalanceStorm["Consumer Rebalance Storm"]
        DeserializationDeadlock["Poison Pill Crash Loop"]
        FixRebalance["Reduce max.poll.records & Increase max.poll.interval.ms"]
        FixPoison["Configure ErrorHandlingDeserializer"]
    end

    Issue --> DBSpike
    Issue --> LagSpike
    
    DBSpike --> CheckTTL
    CheckTTL -->|Single Hot Key| Stampede
    CheckTTL -->|Mass Keys| Avalanche
    Stampede --> FixStampede
    Avalanche --> FixAvalanche

    LagSpike --> PollTimeout
    LagSpike --> PoisonPill
    PollTimeout -->|Yes| RebalanceStorm
    PoisonPill -->|Yes| DeserializationDeadlock
    RebalanceStorm --> FixRebalance
    DeserializationDeadlock --> FixPoison
```

---

## 2. Pitfall 1: Redis Cache Stampede (Thundering Herd)

### Symptom Log & Metrics
PostgreSQL connection pool exhausted (`CannotGetJdbcConnectionException`) immediately after a hot key (e.g. `products::top_deals`) expires in Redis under 20,000 req/sec.

### Root Cause
When the hot key expires, 2,000 concurrent threads simultaneously experience a cache miss. Each thread executes the expensive DB query independently and writes identical data back to Redis.

### Resolution
Enable Spring's built-in single-JVM synchronization lock or implement a distributed mutex with Redis `SETNX`:

```java
// ✅ RESOLUTION 1: JVM-Level Synchronization Lock
@Cacheable(value = "products", key = "#id", sync = true)
public ProductDto getProductById(Long id) {
    return productRepository.findById(id).map(ProductDto::from).orElseThrow();
}
```

```java
// ✅ RESOLUTION 2: Distributed Key Expiration Jitter
@Bean
public RedisCacheConfiguration defaultCacheConfig() {
    return RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(10).plusSeconds(ThreadLocalRandom.current().nextInt(60, 300)))
            .serializeValuesWith(SerializationPair.fromSerializer(new GenericJackson2JsonRedisSerializer()));
}
```

---

## 3. Pitfall 2: Kafka Consumer Rebalance Storms (`CommitFailedException`)

### Symptom Log
```text
org.apache.kafka.clients.consumer.CommitFailedException: 
Offset commit cannot be completed since the group has already rebalanced and assigned the partitions to another member. 
This means that the time between consecutive calls to poll() was longer than the configured max.poll.interval.ms.
```

### Root Cause
The consumer polled a batch of 500 records. Because each record required a 1,000ms external API call or database write, total batch execution took 500 seconds—far exceeding the default `max.poll.interval.ms` (300 seconds / 5 minutes). Kafka considered the consumer dead, evicted it from the group, triggered a cluster rebalance, and re-delivered the same 500 records to another consumer, triggering an endless rebalance storm.

### Resolution
Tune batch size and poll timeout in `application.yml`:

```yaml
spring:
  kafka:
    consumer:
      # Reduce batch size so processing finishes well within the poll timeout
      max-poll-records: 50
      properties:
        # Increase max poll interval to accommodate worst-case latencies
        max.poll.interval.ms: 600000 # 10 minutes
        # Keep heartbeat frequency high
        heartbeat.interval.ms: 3000
        session.timeout.ms: 45000
```

---

## 4. Pitfall 3: Kafka Poison Pill Deserialization Deadlock

### Symptom Log
```text
org.apache.kafka.common.errors.SerializationException: 
Error deserializing key/value for partition order-events-0 at offset 14221
Caused by: com.fasterxml.jackson.core.JsonParseException: Unexpected character ('<' (code 60))
```

### Root Cause
An upstream service sent an HTML error response or corrupted payload. The standard `JsonDeserializer` throws an exception directly inside `KafkaConsumer.poll()`. Because the record is never passed to `@KafkaListener`, the offset is never acknowledged, and on the next poll, Kafka attempts to deserialize the exact same invalid record, deadlocking the consumer forever.

### Resolution
Wrap deserializers inside `ErrorHandlingDeserializer`:

```yaml
spring:
  kafka:
    consumer:
      key-deserializer: org.springframework.kafka.support.serializer.ErrorHandlingDeserializer
      value-deserializer: org.springframework.kafka.support.serializer.ErrorHandlingDeserializer
      properties:
        spring.deserializer.key.delegate.class: org.apache.kafka.common.serialization.StringDeserializer
        spring.deserializer.value.delegate.class: org.springframework.kafka.support.serializer.JsonDeserializer
        spring.json.trusted.packages: "com.example.*"
```

---

## 🧭 Navigation & Diagnostic Playbooks

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Troubleshooting Spring Boot Testing & Testcontainers**](spring-boot-testing-and-testcontainers-pitfalls.md) | [**All Debugging Guides**](index.md) | [➡️ **Troubleshooting Microservices & SAGA**](microservices-circuit-breaker-and-distributed-transaction-pitfalls.md) |
