---
icon: lucide/workflow
---

# 0055: Kafka Producer & Consumer Integration with Spring Kafka & DLQ

Building resilient event-driven microservices requires more than simple message sending. In production, networks drop packets, databases deadlock, and malformed payloads ("poison pills") can trap consumers in infinite retry loops that stall entire partition pipelines.

**Spring for Apache Kafka (`spring-kafka`)** provides high-level abstractions (`KafkaTemplate`, `@KafkaListener`, `@RetryableTopic`, `DefaultErrorHandler`) to manage delivery guarantees, manual acknowledgments, non-blocking retries, and automated **Dead Letter Queues (DLQ)**.

In this lesson, you will master configuring idempotent producers, manual offset acknowledgment, non-blocking retry topics with exponential backoff, and poison-pill deserialization handlers.

---

## 1. Resilient Kafka Event & DLQ Architecture

``` mermaid
flowchart TD
    subgraph ProducerService["Order Service (Producer)"]
        OrderApp["Order Placement Engine"]
        KafkaTemplate["KafkaTemplate (acks=all, idempotent=true)"]
        OrderApp --> KafkaTemplate
    end

    subgraph KafkaBroker["Kafka Cluster"]
        MainTopic["Topic: 'order-events' (Partitions 0..2)"]
        RetryTopic["Topic: 'order-events.RETRY' (Retry Buffer)"]
        DLQTopic["Topic: 'order-events.DLT' (Dead Letter Queue)"]
    end

    subgraph ConsumerService["Payment Service (Consumer)"]
        Listener["@KafkaListener / @RetryableTopic"]
        Processor["Payment Processor"]
        ErrorHandler["DefaultErrorHandler (3 Retries + Exponential Backoff)"]
        DLQConsumer["DLQ Error Handler & Alerting Service"]
    end

    KafkaTemplate -->|1. Idempotent Send| MainTopic
    MainTopic -->|2. Consume Record| Listener
    Listener --> Processor

    Processor -.->|3. Success| Ack["Ack Offset (MANUAL_IMMEDIATE)"]
    Processor -.->|4. Transient Failure| ErrorHandler
    ErrorHandler -.->|5. Retry Exceeded| DLQTopic

    DLQTopic --> DLQConsumer
    DLQConsumer --> Alert["PagerDuty / Slack Alert + Storage"]
```

---

## 2. Maven Dependencies (`pom.xml`)

```xml
<dependency>
    <groupId>org.springframework.kafka</groupId>
    <artifactId>spring-kafka</artifactId>
</dependency>
<dependency>
    <groupId>com.fasterxml.jackson.core</groupId>
    <artifactId>jackson-databind</artifactId>
</dependency>
```

---

## 3. Production Producer Configuration (`KafkaProducerConfig`)

To guarantee zero data loss and prevent duplicate messages during network partitions, configure the producer with `acks=all` and `enable.idempotence=true`:

```java
package com.example.config;

import com.example.dto.OrderEvent;
import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.kafka.support.serializer.JsonSerializer;

import java.util.HashMap;
import java.util.Map;

@Configuration
public class KafkaProducerConfig {

    @Value("${spring.kafka.bootstrap-servers:localhost:9092}")
    private String bootstrapServers;

    @Bean
    public ProducerFactory<String, OrderEvent> orderProducerFactory() {
        Map<String, Object> props = new HashMap<>();
        props.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        props.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, JsonSerializer.class);
        
        // 🔒 High-Reliability & Zero Data Loss Settings
        props.put(ProducerConfig.ACKS_CONFIG, "all");                         // Wait for full ISR acknowledgment
        props.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);            // Prevent duplicate broker writes
        props.put(ProducerConfig.RETRIES_CONFIG, Integer.MAX_VALUE);          // Retry on transient network blips
        props.put(ProducerConfig.MAX_IN_FLIGHT_REQUESTS_PER_CONNECTION, 5);  // Preserve order with idempotence enabled
        
        return new DefaultKafkaProducerFactory<>(props);
    }

    @Bean
    public KafkaTemplate<String, OrderEvent> kafkaTemplate(ProducerFactory<String, OrderEvent> pf) {
        return new KafkaTemplate<>(pf);
    }
}
```

### Publishing Messages with Asynchronous Callbacks

```java
package com.example.producer;

import com.example.dto.OrderEvent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Service;

import java.util.concurrent.CompletableFuture;

@Slf4j
@Service
@RequiredArgsConstructor
public class OrderEventProducer {

    private final KafkaTemplate<String, OrderEvent> kafkaTemplate;
    public static final String TOPIC_ORDERS = "order-events";

    public void sendOrderEvent(OrderEvent event) {
        // Message key ensures all updates for this customer land in the exact same partition
        String messageKey = event.customerId();

        CompletableFuture<SendResult<String, OrderEvent>> future = 
                kafkaTemplate.send(TOPIC_ORDERS, messageKey, event);

        future.whenComplete((result, ex) -> {
            if (ex == null) {
                log.info("Event published successfully: topic={}, partition={}, offset={}, key={}",
                        result.getRecordMetadata().topic(),
                        result.getRecordMetadata().partition(),
                        result.getRecordMetadata().offset(),
                        messageKey);
            } else {
                log.error("CRITICAL: Failed to publish event for key={}", messageKey, ex);
                // Trigger fallback outbox or alerting
            }
        });
    }
}
```

---

## 4. Consumer Configuration with Poison-Pill Protection

> [!CAUTION]
> **The Poison Pill Trap**: If a producer writes a malformed JSON payload to Kafka, standard deserializers throw a `SerializationException` inside the Kafka polling loop **before** your listener code runs. This halts consumer progress forever unless handled via `ErrorHandlingDeserializer`.

```java
package com.example.config;

import com.example.dto.OrderEvent;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.kafka.config.ConcurrentKafkaListenerContainerFactory;
import org.springframework.kafka.core.ConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.listener.ContainerProperties;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.kafka.support.serializer.ErrorHandlingDeserializer;
import org.springframework.kafka.support.serializer.JsonDeserializer;
import org.springframework.util.backoff.FixedBackOff;

import java.util.HashMap;
import java.util.Map;

@EnableKafka
@Configuration
public class KafkaConsumerConfig {

    @Value("${spring.kafka.bootstrap-servers:localhost:9092}")
    private String bootstrapServers;

    @Bean
    public ConsumerFactory<String, OrderEvent> orderConsumerFactory() {
        Map<String, Object> props = new HashMap<>();
        props.put(ConsumerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        props.put(ConsumerConfig.GROUP_ID_CONFIG, "payment-service-group");
        props.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        props.put(ConsumerConfig.ENABLE_AUTO_COMMIT_CONFIG, false); // Manual ack to avoid losing messages

        // Wrapping deserializers in ErrorHandlingDeserializer to catch poison pills
        props.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, ErrorHandlingDeserializer.class);
        props.put(ErrorHandlingDeserializer.KEY_DESERIALIZER_CLASS, StringDeserializer.class);

        props.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ErrorHandlingDeserializer.class);
        props.put(ErrorHandlingDeserializer.VALUE_DESERIALIZER_CLASS, JsonDeserializer.class);
        props.put(JsonDeserializer.TRUSTED_PACKAGES, "com.example.dto");

        return new DefaultKafkaConsumerFactory<>(props);
    }

    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, OrderEvent> kafkaListenerContainerFactory(
            ConsumerFactory<String, OrderEvent> consumerFactory) {
        
        ConcurrentKafkaListenerContainerFactory<String, OrderEvent> factory =
                new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory);
        factory.setConcurrency(3); // 3 worker threads matching partition count
        
        // Manual immediate offset commit
        factory.getContainerProperties().setAckMode(ContainerProperties.AckMode.MANUAL_IMMEDIATE);
        
        // Default error handler: 3 retries with 1000ms delay before forwarding
        factory.setCommonErrorHandler(new DefaultErrorHandler(new FixedBackOff(1000L, 3)));
        
        return factory;
    }
}
```

---

## 5. Modern Non-Blocking Retries & Dead Letter Queue with `@RetryableTopic`

Spring Kafka 2.7+ introduced `@RetryableTopic`, which creates separate non-blocking retry topics and a Dead Letter Topic (`-dlt`) automatically:

```java
package com.example.consumer;

import com.example.dto.OrderEvent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.DltHandler;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.annotation.RetryableTopic;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.retry.annotation.Backoff;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class OrderEventConsumer {

    /**
     * Non-blocking retries: If an exception occurs, the record is routed to a retry topic
     * with exponential backoff (1s, 2s, 4s) up to 3 attempts, without blocking other records!
     */
    @RetryableTopic(
            attempts = "3",
            backoff = @Backoff(delay = 1000, multiplier = 2.0),
            autoCreateTopics = "true"
    )
    @KafkaListener(topics = "order-events", groupId = "payment-service-group")
    public void consumeOrder(
            @Payload OrderEvent event,
            @Header(KafkaHeaders.RECEIVED_PARTITION) int partition,
            @Header(KafkaHeaders.OFFSET) long offset,
            Acknowledgment ack) {
        
        log.info("Processing order event [ID: {}] from partition {}, offset {}", 
                event.orderId(), partition, offset);

        if (event.totalAmount() == null || event.totalAmount().doubleValue() < 0) {
            throw new IllegalArgumentException("Invalid order amount: " + event.totalAmount());
        }

        // Business logic execution...
        log.info("Payment processed successfully for order: {}", event.orderId());

        // Acknowledge offset to Kafka
        ack.acknowledge();
    }

    /**
     * DLT (Dead Letter Topic) Handler: Triggered when all retry attempts are exhausted.
     */
    @DltHandler
    public void handleDltMessage(
            @Payload OrderEvent event,
            @Header(KafkaHeaders.RECEIVED_TOPIC) String topic,
            @Header(KafkaHeaders.OFFSET) long offset,
            Acknowledgment ack) {
        
        log.error("CRITICAL: Message permanently moved to DLT [Topic: {}, Offset: {}]. Payload: {}", 
                topic, offset, event);
        
        // Save to failed_events database or trigger PagerDuty alert
        ack.acknowledge();
    }
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Error Handling Architecture** | `CommonErrorHandler` / `DefaultErrorHandler` replacing deprecated `SeekToCurrentErrorHandler`. | Unified reactive and imperative error recovery pipelines with zero-copy DLT redirection. |
| **Virtual Thread Support** | Container factories run with platform threads unless explicitly hooked to `SimpleAsyncTaskExecutor`. | Native Virtual Thread worker dispatchers configured by default with `spring.threads.virtual.enabled=true`. |
| **Distributed Tracing** | Micrometer Tracing auto-propagates `traceparent` metadata across Kafka message headers. | Native OpenTelemetry OTLP tracing context extraction and W3C Baggage carrier injection. |

---

## 7. Primary Sources & Further Reading

- [Spring for Apache Kafka Documentation](https://docs.spring.io/spring-kafka/reference/) — `@KafkaListener`, `@RetryableTopic`, and `DefaultErrorHandler`.
- [Apache Kafka Producer Configurations](https://kafka.apache.org/documentation/#producerconfigs) — `acks`, `enable.idempotence`, and retry parameters.
- [Spring Kafka Non-Blocking Retries and DLT](https://docs.spring.io/spring-kafka/reference/kafka/annotation-error-handling.html#retry-topic).

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: Why is `enable.idempotence=true` essential for Kafka producers in distributed systems?"
    **Answer**: It prevents duplicate messages from being written to the broker when network timeouts cause the producer to retry sending an already-persisted record.

??? question "Question 2: What problem does `ErrorHandlingDeserializer` solve?"
    **Answer**: It intercepts poison-pill deserialization exceptions before they crash the Kafka listener polling loop, preventing consumers from stalling in an infinite deserialization crash.

??? question "Question 3: How does `@RetryableTopic` prevent slow retries from blocking other messages in the same partition?"
    **Answer**: It republishes failed records to separate retry topics with backoff delays, allowing the main topic partition to keep processing subsequent messages without delay.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0054: Apache Kafka Architecture: Topics, Partitions & Consumer Groups**](0054-apache-kafka-architecture-and-internals.md) | [**All Lessons**](index.md) | [➡️ **0056: Rate Limiting Algorithms in Redis: Token Bucket & Sliding Window**](0056-redis-rate-limiting-algorithms.md) |

🎉 **Lesson 0055 completed! Proceed to Lesson 0056 to master high-throughput Redis rate limiting algorithms.**
