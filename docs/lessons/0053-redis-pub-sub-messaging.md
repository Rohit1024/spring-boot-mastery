---
icon: lucide/radio
---

# 0053: Redis Pub/Sub messaging for real-time event fanout

In distributed microservices, services often need to broadcast lightweight events to all running instances simultaneously. Common examples include:
- **Distributed Cache Invalidation**: Informing 50 microservice pods to instantly purge their local in-memory (Caffeine L1) cache when data changes in the database.
- **WebSocket Broadcast**: Relaying a chat message or notification across horizontally scaled WebSocket nodes.

**Redis Pub/Sub (Publish/Subscribe)** provides ultra-fast, fire-and-forget message broadcasting with zero broker setup overhead.

In this lesson, you will master configuring `RedisMessageListenerContainer`, building typed event publishers and subscribers, and contrasting Redis Pub/Sub with persistent brokers like Apache Kafka.

---

## 1. Redis pub/sub fanout architecture

``` mermaid
flowchart TD
    subgraph PublisherNode["Publisher: Instance A (Spring Boot)"]
        EventService["OrderEventService"]
        RedisTemplate["RedisTemplate (PUBLISH order-events)"]
        EventService --> RedisTemplate
    end

    subgraph RedisBroker["Redis Server (In-Memory Pub/Sub Router)"]
        ChannelTopic["Channel: 'order-events'"]
        RedisTemplate -->|TCP PUBLISH Payload| ChannelTopic
    end

    subgraph SubscriberNodes["Subscriber Replicas (Fanout Delivery)"]
        subgraph NodeB["Instance B (Replica 1)"]
            ListenerContainerB["RedisMessageListenerContainer"]
            HandlerB["OrderEventListener (Purge L1 Cache)"]
            ListenerContainerB --> HandlerB
        end

        subgraph NodeC["Instance C (Replica 2)"]
            ListenerContainerC["RedisMessageListenerContainer"]
            HandlerC["OrderEventListener (Push WebSocket Alert)"]
            ListenerContainerC --> HandlerC
        end

        subgraph NodeD["Instance D (Replica 3)"]
            ListenerContainerD["RedisMessageListenerContainer"]
            HandlerD["OrderEventListener (Update Metrics)"]
            ListenerContainerD --> HandlerD
        end

        ChannelTopic -->|Instant TCP Fanout| ListenerContainerB
        ChannelTopic -->|Instant TCP Fanout| ListenerContainerC
        ChannelTopic -->|Instant TCP Fanout| ListenerContainerD
    end
```

---

## 2. Pub/sub vs message queues vs Kafka

Understanding when to use Redis Pub/Sub versus persistent queues is critical for distributed system design:

| Characteristic | Redis Pub/Sub | Redis Streams | Apache Kafka |
| :--- | :--- | :--- | :--- |
| **Delivery Semantics** | At-most-once (Fire & Forget). | At-least-once with Consumer Groups. | At-least-once / Exactly-once (Transactional). |
| **Persistence** | None (Messages dropped if subscriber is offline). | Stored in Redis RAM / RDB / AOF log. | High-durability disk-backed partitioned log. |
| **Replayability** | ❌ Impossible (No historical log). | ✅ Offset / ID-based message replay. | ✅ Replay by offset across retention period. |
| **Latency** | Sub-millisecond (< 1ms). | Low (< 5ms). | Low-to-medium (2-15ms batch-dependent). |
| **Primary Use Cases** | Cache invalidations, live UI notifications, WebSocket routing. | Work queues, simple event sourcing, task pipelines. | Enterprise event backbone, analytics, financial ledgers. |

---

## 3. Publisher implementation

Publish events using `RedisTemplate.convertAndSend()`:

```java
package com.example.publisher;

import com.example.dto.OrderEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class OrderEventPublisher {

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper;
    public static final String ORDER_TOPIC = "events.orders";

    public void publishOrderCreated(OrderEvent event) {
        try {
            String payload = objectMapper.writeValueAsString(event);
            log.info("Broadcasting event to Redis topic '{}': {}", ORDER_TOPIC, payload);
            redisTemplate.convertAndSend(ORDER_TOPIC, payload);
        } catch (Exception e) {
            log.error("Failed to publish order event to Redis", e);
            throw new RuntimeException("Redis publish failure", e);
        }
    }
}
```

---

## 4. Subscriber container configuration

In Spring Data Redis, `RedisMessageListenerContainer` maintains long-lived listening connections to the Redis server and dispatches received messages across worker threads:

```java
package com.example.config;

import com.example.listener.OrderEventListener;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.data.redis.listener.PatternTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.data.redis.listener.adapter.MessageListenerAdapter;

@Configuration
public class RedisPubSubConfig {

    @Bean
    public ChannelTopic orderChannelTopic() {
        return new ChannelTopic("events.orders");
    }

    @Bean
    public MessageListenerAdapter orderListenerAdapter(OrderEventListener orderEventListener) {
        // Delegates incoming messages to 'receiveMessage' method on listener bean
        return new MessageListenerAdapter(orderEventListener, "receiveMessage");
    }

    @Bean
    public RedisMessageListenerContainer redisMessageListenerContainer(
            RedisConnectionFactory connectionFactory,
            MessageListenerAdapter orderListenerAdapter,
            ChannelTopic orderChannelTopic) {
        
        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);
        
        // Exact Channel Subscription
        container.addMessageListener(orderListenerAdapter, orderChannelTopic);
        
        // Optional: Pattern-based Subscription (e.g., all events.*)
        // container.addMessageListener(orderListenerAdapter, new PatternTopic("events.*"));
        
        return container;
    }
}
```

---

## 5. Event listener implementation

```java
package com.example.listener;

import com.example.dto.OrderEvent;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.CacheManager;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class OrderEventListener {

    private final ObjectMapper objectMapper;
    private final CacheManager cacheManager;

    /**
     * Invoked automatically by MessageListenerAdapter when a message arrives on 'events.orders'
     */
    public void receiveMessage(String message, String channel) {
        log.info("Received Redis pub/sub message on channel [{}]: {}", channel, message);
        try {
            OrderEvent event = objectMapper.readValue(message, OrderEvent.class);
            
            // Example: Evict local in-memory L1 cache on this pod
            if (cacheManager.getCache("orders") != null) {
                cacheManager.getCache("orders").evict(event.orderId());
                log.info("Local L1 cache evicted for order ID: {}", event.orderId());
            }
            
        } catch (Exception e) {
            log.error("Failed to deserialize or process Redis Pub/Sub message", e);
        }
    }
}
```

---

## 6. Connection pool threading considerations

> [!WARNING]
> **Dedicated Redis Connections**: Every active `RedisMessageListenerContainer` subscribes to Redis using a **blocking, dedicated TCP connection** that remains continuously open and cannot be used for standard Redis read/write commands (`GET`, `SET`).
> Ensure your Lettuce connection pool sizing (`spring.data.redis.lettuce.pool.max-active`) accounts for dedicated pub/sub connections plus standard data operations.

---

## 7. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Listener Threading** | Dedicated ThreadPoolTaskExecutor managing worker threads per subscription. | Virtual-thread-backed listener dispatchers eliminating platform thread overhead during high connection counts. |
| **Reactive Pub/Sub** | `ReactiveRedisTemplate.listenToChannel()` returning Project Reactor `Flux<Message>`. | First-class reactive backpressure handling and automated reconnection lifecycle management. |
| **Observability** | Manual Micrometer timer instrumentation on message arrival. | Automatic OTel span creation per published and received Redis Pub/Sub frame. |

---

## 8. Primary sources and further reading

- [Redis Pub/Sub Specification](https://redis.io/docs/interact/pubsub/), Details on `SUBSCRIBE`, `PUBLISH`, and pattern matching (`PSUBSCRIBE`).
- [Spring Data Redis Messaging Documentation](https://docs.spring.io/spring-data/redis/reference/redis/messaging.html), `RedisMessageListenerContainer` and `MessageListenerAdapter`.
- [Enterprise Integration Patterns: Publish-Subscribe Channel](https://www.enterpriseintegrationpatterns.com/patterns/messaging/PublishSubscribeChannel.html).

---

## 9. Knowledge check and practice

??? question "Question 1: What happens to a Redis Pub/Sub message if a subscriber pod is momentarily restarting during publication?"
    **Answer**: The message is permanently lost for that restarting subscriber because Redis Pub/Sub is ephemeral and does not retain messages in a buffer or queue.

??? question "Question 2: What is the primary architectural use case for Redis Pub/Sub compared to Apache Kafka?"
    **Answer**: Real-time ephemeral broadcasting (such as multi-instance local L1 cache invalidations and WebSocket fanout) where persistence and replay are not required.

??? question "Question 3: Why does `RedisMessageListenerContainer` require a dedicated connection from the connection pool?"
    **Answer**: When a client executes `SUBSCRIBE`, the Redis connection enters a dedicated subscription state and cannot process regular commands like `GET` or `SET`.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0052: Spring Cache Abstraction with Redis**](0052-spring-cache-abstraction-redis.md) | [**All Lessons**](index.md) | [ **0054: Apache Kafka Architecture: Topics, Partitions & Consumer Groups**](0054-apache-kafka-architecture-and-internals.md) |

🎉 **Lesson 0053 completed! Proceed to Lesson 0054 to master Apache Kafka distributed architecture and commit log internals.**
