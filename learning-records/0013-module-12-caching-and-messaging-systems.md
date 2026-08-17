# Learning Record 0013: Module 12 — High-Performance Caching & Messaging Systems Completed

- **Date**: 2026-08-17
- **Module**: Module 12: High-Performance Caching & Messaging Systems (Redis, Spring Cache, Redis Pub/Sub, Apache Kafka, DLQ, Rate Limiting)
- **Status**: Completed

## Concepts Mastered

1. **Spring Cache Abstraction with Redis**:
   - Declarative caching with `@Cacheable`, `@CachePut`, `@CacheEvict`, and `@Caching`.
   - `RedisCacheManager` configuration with `GenericJackson2JsonRedisSerializer` and granular per-cache TTLs.
   - Mitigating Cache Stampede using `@Cacheable(sync = true)` and distributed lock patterns.
   - Defending against Cache Penetration (null object caching) and Cache Avalanche (randomized TTL jitter).

2. **Redis Pub/Sub Messaging for Real-Time Event Fanout**:
   - Ephemeral, fire-and-forget message broadcasting with `PUBLISH`, `SUBSCRIBE`, and `PSUBSCRIBE`.
   - Configuring `RedisMessageListenerContainer`, `MessageListenerAdapter`, `ChannelTopic`, and `PatternTopic`.
   - Architectural comparison: Redis Pub/Sub vs Redis Streams vs Apache Kafka.
   - Use cases: Distributed L1 in-memory (Caffeine) cache invalidation across microservice pods and real-time WebSocket cluster synchronization.

3. **Apache Kafka Architecture & Disk Storage Internals**:
   - Distributed append-only commit log model, Topics, Partitions, and Segment files (`.log`, `.index`, `.timeindex`).
   - High-throughput disk mechanics: Sequential disk I/O, OS PageCache utilization, and zero-copy `sendfile` network transfer.
   - Partitioning mechanics via Murmur2 hashing and strict single-partition ordering guarantees.
   - Consumer Groups, Rebalance protocols (Eager vs Cooperative Sticky Rebalance), Offsets (`__consumer_offsets`), High Watermark (HW), Log End Offset (LEO), and In-Sync Replicas (ISR).
   - Metadata evolution: KRaft (Kafka Raft consensus) replacing legacy Apache ZooKeeper.

4. **Spring Kafka Producers, Consumers & Dead Letter Queues (DLQ)**:
   - Producer reliability: `acks=all`, `enable.idempotence=true`, `retries=Integer.MAX_VALUE`, and asynchronous `CompletableFuture` send callbacks.
   - Consumer resilience: Manual acknowledgment with `AckMode.MANUAL_IMMEDIATE` and `Acknowledgment.acknowledge()`.
   - Poison pill prevention using `ErrorHandlingDeserializer` for keys and values.
   - Non-blocking retry topics with exponential backoff and Dead Letter Topic (DLT) dispatch via `@RetryableTopic` and `@DltHandler`.

5. **Distributed Rate Limiting with Redis & Lua Scripting**:
   - Comparison of 4 rate limiting algorithms: Fixed Window Counter, Sliding Window Log, Sliding Window Counter, and Token Bucket.
   - Authoring atomic Redis Lua scripts (`redis.call()`, `EVALSHA`) to prevent race conditions under high concurrency without distributed locks.
   - Spring MVC `HandlerInterceptor` integration enforcing RFC-compliant HTTP `429 Too Many Requests` with `X-RateLimit-*` and `Retry-After` headers.

## Artifacts Produced

- Lessons: `0052`, `0053`, `0054`, `0055`, `0056` (with Spring Boot 3 vs 4 comparisons and vertical Mermaid diagrams).
- Cheatsheet: `docs/cheatsheet/redis-caching-and-kafka-messaging.md`.
- Debugging Guide: `docs/debugging/redis-cache-stampede-and-kafka-consumer-lag.md`.
- Interview Questions: 11 high-signal Caching, Redis, and Kafka questions in `docs/interview/index.md`.
- Glossary: Added definitions for Cache-Aside, Cache Stampede, Cache Penetration, Cache Avalanche, Redis Pub/Sub, Kafka Partition, Consumer Group, In-Sync Replicas (ISR), High Watermark (HW), KRaft, Dead Letter Topic (DLT), ErrorHandlingDeserializer, and Token Bucket.
- Resources: Added official Spring Data Redis and Spring for Apache Kafka reference links in `docs/references/resources.md`.
