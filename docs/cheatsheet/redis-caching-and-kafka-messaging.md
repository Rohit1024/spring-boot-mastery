---
icon: lucide/file-code
---

# Redis Caching, Pub/Sub & Apache Kafka Cheatsheet

A production-ready reference card for Spring Cache with Redis, Redis Pub/Sub, Apache Kafka producers/consumers, non-blocking DLQ retries, and Redis Lua rate limiting.

---

## 1. Spring Cache with Redis Annotations

| Annotation | Attribute | Purpose / Example |
| :--- | :--- | :--- |
| **`@Cacheable`** | `value`, `key`, `unless`, `condition`, `sync` | Caches method return value. `@Cacheable(value = "users", key = "#id", sync = true)` |
| **`@CachePut`** | `value`, `key` | Always executes method and updates the cache. `@CachePut(value = "users", key = "#user.id")` |
| **`@CacheEvict`** | `value`, `key`, `allEntries` | Removes entry from cache. `@CacheEvict(value = "users", key = "#id")` or `allEntries = true` |
| **`@Caching`** | `cacheable`, `put`, `evict` | Combines multiple cache operations on a single method. |

```java
// RedisCacheConfiguration with JSON Serialization & Custom TTLs
@Bean
public RedisCacheConfiguration defaultCacheConfig() {
    return RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(10))
            .disableCachingNullValues()
            .serializeKeysWith(SerializationPair.fromSerializer(new StringRedisSerializer()))
            .serializeValuesWith(SerializationPair.fromSerializer(new GenericJackson2JsonRedisSerializer()));
}
```

---

## 2. Redis Pub/Sub Messaging Quick Reference

```java
// Publisher
redisTemplate.convertAndSend("events.orders", jsonPayload);

// Subscriber Container Configuration
@Bean
public RedisMessageListenerContainer container(RedisConnectionFactory factory, MessageListenerAdapter adapter) {
    RedisMessageListenerContainer container = new RedisMessageListenerContainer();
    container.setConnectionFactory(factory);
    container.addMessageListener(adapter, new ChannelTopic("events.orders"));
    return container;
}
```

---

## 3. Kafka Producer & Consumer Configuration Matrix

| Parameter | Recommended Setting | Production Rationale |
| :--- | :--- | :--- |
| `acks` | `"all"` (`-1`) | Guarantees all In-Sync Replicas (ISR) have written the record before returning success. |
| `enable.idempotence` | `true` | Prevents duplicate messages on network retries without ordering degradation. |
| `retries` | `Integer.MAX_VALUE` | Ensures transient broker failovers do not cause message drops. |
| `max.in.flight.requests.per.connection` | `5` | Keeps high pipelined throughput while preserving partition order with idempotence enabled. |
| `enable.auto.commit` | `false` | Prevents lost records on consumer crash; use `AckMode.MANUAL_IMMEDIATE`. |
| `auto.offset.reset` | `"earliest"` | New consumer groups read from beginning of partition log rather than dropping historical records. |

---

## 4. Spring Kafka `@RetryableTopic` & Dead Letter Queue (DLQ)

```java
@RetryableTopic(
        attempts = "4",
        backoff = @Backoff(delay = 1000, multiplier = 2.0, maxDelay = 10000),
        autoCreateTopics = "true",
        include = {TransientNetworkException.class}
)
@KafkaListener(topics = "orders-topic", groupId = "order-group")
public void processOrder(@Payload OrderDto order, Acknowledgment ack) {
    orderService.process(order);
    ack.acknowledge(); // Manual ACK
}

@DltHandler
public void processDlt(@Payload OrderDto order, @Header(KafkaHeaders.RECEIVED_TOPIC) String topic) {
    log.error("Exhausted retries. Message moved to DLQ [Topic: {}]: {}", topic, order);
}
```

---

## 5. Redis Token Bucket Rate Limiter (Lua Script)

```lua
-- KEYS[1] = ratelimit:user_123, ARGV[1] = capacity, ARGV[2] = refill_rate_per_sec, ARGV[3] = now_sec
local data = redis.call("HMGET", KEYS[1], "tokens", "last_refill")
local tokens = tonumber(data[1]) or tonumber(ARGV[1])
local last_refill = tonumber(data[2]) or tonumber(ARGV[3])

local elapsed = math.max(0, tonumber(ARGV[3]) - last_refill)
tokens = math.min(tonumber(ARGV[1]), tokens + elapsed * tonumber(ARGV[2]))

if tokens >= 1 then
    tokens = tokens - 1
    redis.call("HMSET", KEYS[1], "tokens", tokens, "last_refill", ARGV[3])
    redis.call("EXPIRE", KEYS[1], math.ceil(tonumber(ARGV[1]) / tonumber(ARGV[2])) * 2)
    return {1, math.floor(tokens)} -- Allowed
else
    return {0, math.floor(tokens)} -- Rate Limited (HTTP 429)
end
```

---

## 🧭 Navigation & Cheatsheet Index

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Enterprise Testing & Testcontainers Cheatsheet**](enterprise-testing-and-testcontainers.md) | [**All Cheatsheets**](index.md) | [➡️ **Microservices & Kubernetes Cheatsheet**](microservices-kubernetes-and-cloud-cicd.md) |
