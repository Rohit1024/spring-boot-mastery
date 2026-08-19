---
icon: lucide/database-zap
---

# 0052: Spring Cache abstraction with Redis

High-throughput applications spend substantial CPU cycles and database I/O executing identical database queries. Direct disk or index lookups introduce latency (10-100ms) that degrades throughput under heavy traffic.

**Redis** is an in-memory, key-value data structure store capable of sub-millisecond read/write latencies. **Spring Cache Abstraction** decouples caching logic from business logic using transparent method annotations (`@Cacheable`, `@CachePut`, `@CacheEvict`), managed by a unified `CacheManager`.

In this lesson, you will master configuring `RedisCacheManager` with JSON serialization, tuning granular per-cache TTLs, using SpEL expressions for conditional caching, and preventing common caching pitfalls.

---

## 1. Spring cache architecture with Redis

``` mermaid
flowchart TD
    subgraph ClientLayer["Client & Controller"]
        ClientReq["HTTP Client Request"]
        Controller["ProductController"]
    end

    subgraph SpringAOP["Spring Caching Aspect (AOP Proxy)"]
        CacheInterceptor["CacheInterceptor (Around Advice)"]
        SpELEval["SpEL Key & Condition Evaluator"]
    end

    subgraph CacheLayer["Redis In-Memory Cache"]
        RedisCacheMgr["RedisCacheManager"]
        RedisCache["Redis Cache: 'products'"]
        RedisStore[("Redis Cluster / Standalone (RAM)")]
    end

    subgraph PersistenceLayer["Primary Persistence Store"]
        ProductRepo["ProductRepository (Spring Data JPA)"]
        Database[("PostgreSQL Database (Disk)")]
    end

    ClientReq --> Controller
    Controller --> CacheInterceptor
    CacheInterceptor --> SpELEval
    SpELEval --> RedisCacheMgr
    RedisCacheMgr --> RedisCache
    RedisCache --> RedisStore

    RedisCache -.->|1. Cache Hit sub-ms| CacheInterceptor
    RedisCache -.->|2. Cache Miss Delegate to DB| ProductRepo
    ProductRepo --> Database
    Database --> ProductRepo
    ProductRepo -.->|3. Populate Cache| RedisCache
```

---

## 2. Maven dependencies (`pomxml`)

Include Spring Data Redis and the Lettuce driver connection pool:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>
<dependency>
    <groupId>org.apache.commons</groupId>
    <artifactId>commons-pool2</artifactId>
</dependency>
```

---

## 3. Production `RedisCacheManager` configuration

By default, Spring Boot serializes cache values using Java standard serialization (`JdkSerializationRedisSerializer`), producing unreadable binary payloads and fragile class-versioning issues. In production, configure `GenericJackson2JsonRedisSerializer` with dynamic per-cache TTLs:

```java
package com.example.config;

import org.springframework.boot.autoconfigure.cache.RedisCacheManagerBuilderCustomizer;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext.SerializationPair;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;

@Configuration
@EnableCaching
public class RedisConfig {

    @Bean
    public RedisCacheConfiguration defaultCacheConfig() {
        return RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(10)) // Default fallback TTL
                .disableCachingNullValues()       // Prevent storing null values unless required
                .serializeKeysWith(SerializationPair.fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(SerializationPair.fromSerializer(new GenericJackson2JsonRedisSerializer()));
    }

    @Bean
    public RedisCacheManagerBuilderCustomizer redisCacheManagerBuilderCustomizer() {
        return builder -> builder
                .withCacheConfiguration("products",
                        RedisCacheConfiguration.defaultCacheConfig()
                                .entryTtl(Duration.ofHours(1))
                                .serializeValuesWith(SerializationPair.fromSerializer(new GenericJackson2JsonRedisSerializer())))
                .withCacheConfiguration("product-inventory",
                        RedisCacheConfiguration.defaultCacheConfig()
                                .entryTtl(Duration.ofSeconds(30)) // Short TTL for frequently updated data
                                .serializeValuesWith(SerializationPair.fromSerializer(new GenericJackson2JsonRedisSerializer())));
    }
}
```

---

## 4. Cache annotations: `@Cacheable`, `@CachePut` `@CacheEvict`

```java
package com.example.service;

import com.example.dto.ProductResponse;
import com.example.dto.ProductUpdateRequest;
import com.example.exception.ResourceNotFoundException;
import com.example.model.Product;
import com.example.repository.ProductRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.CachePut;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.cache.annotation.Caching;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class ProductService {

    private final ProductRepository productRepository;

    /**
     * Cache-Aside: Reads from Redis first. If absent, executes method and stores result in Redis.
     * SpEL: key constructs the exact Redis key e.g. "products::101".
     * unless: Skips caching if product price is 0.
     */
    @Cacheable(
            value = "products", 
            key = "#id", 
            unless = "#result == null || #result.price() == 0",
            sync = true // Prevents Cache Stampede (locks thread locally per key)
    )
    public ProductResponse getProductById(Long id) {
        log.info("Fetching product {} from primary database...", id);
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Product not found: " + id));
        return new ProductResponse(product.getId(), product.getName(), product.getPrice(), product.getSku());
    }

    /**
     * Updates database AND updates Redis cache with new return value.
     */
    @Transactional
    @CachePut(value = "products", key = "#id")
    public ProductResponse updateProduct(Long id, ProductUpdateRequest request) {
        log.info("Updating product {} in DB and synchronizing cache...", id);
        Product product = productRepository.findById(id)
                .orElseThrow(() -> new ResourceNotFoundException("Product not found: " + id));
        product.setName(request.name());
        product.setPrice(request.price());
        Product saved = productRepository.save(product);
        return new ProductResponse(saved.getId(), saved.getName(), saved.getPrice(), saved.getSku());
    }

    /**
     * Evicts specific entry from 'products' cache and clears entire 'product-inventory' cache.
     */
    @Transactional
    @Caching(evict = {
            @CacheEvict(value = "products", key = "#id"),
            @CacheEvict(value = "product-inventory", allEntries = true)
    })
    public void deleteProduct(Long id) {
        log.info("Deleting product {} and evicting caches...", id);
        if (!productRepository.existsById(id)) {
            throw new ResourceNotFoundException("Product not found: " + id);
        }
        productRepository.deleteById(id);
    }
}
```

---

## 5. Caching strategies distributed pitfalls

| Caching Pattern / Pitfall | Mechanism | Mitigation / Best Practice |
| :--- | :--- | :--- |
| **Cache-Aside (Lazy Loading)** | Application checks cache first; on miss, queries database and populates cache. | Standard default pattern. Use `@Cacheable(sync = true)` to avoid duplicate DB hits under concurrent requests. |
| **Write-Through / Write-Back** | Application writes to cache, and cache synchronously (or asynchronously in background) updates DB. | Use `@CachePut` alongside `@Transactional` for consistent synchronous updates. |
| **Cache Stampede (Thundering Herd)** | High-concurrency access when a hot cache key expires simultaneously causes 10,000 DB queries. | Enable `@Cacheable(sync = true)` for single-JVM synchronization or Redis distributed mutex locks. |
| **Cache Penetration** | Requests query non-existent keys (e.g. `id = -999`), bypassing cache and hammering DB. | Cache null objects with short TTLs (`entryTtl(Duration.ofMinutes(1))`) or use Bloom Filters. |
| **Cache Avalanche** | Thousands of cache keys expire simultaneously, overwhelming the database with batch misses. | Add random jitter (e.g. `TTL = baseTTL + rand(0, 300s)`) to cache expiration durations. |

---

## 6. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Redis Client Engine** | Lettuce 6.x / Jedis with synchronous / non-blocking driver pools. | Lettuce 7.x optimized for Java Virtual Threads with zero carrier thread blocking. |
| **Serialization** | `GenericJackson2JsonRedisSerializer` using Jackson 2.x `@class` typing. | Modular serialization with Jackson 3.x / Jakarta JSON-B and native GraalVM reflection-free hints. |
| **Native Multi-Level Caching** | Requires custom composite cache managers (Caffeine L1 + Redis L2). | Built-in hierarchical L1/L2 multi-tier caching abstractions with automatic pub/sub synchronization. |

---

## 7. Primary sources and further reading

- [Spring Cache Abstraction Documentation](https://docs.spring.io/spring-framework/reference/integration/cache.html), Annotations, SpEL expressions, and `CacheManager` lifecycle.
- [Spring Data Redis Reference Manual](https://docs.spring.io/spring-data/redis/reference/), Lettuce drivers, `RedisCacheConfiguration`, and custom serializers.
- [Redis Official Documentation](https://redis.io/docs/), Data structures, expiration semantics, and Redis Cluster topology.

---

## 8. Knowledge check and practice

??? question "Question 1: What is the difference in behavior between `@Cacheable` and `@CachePut`?"
    **Answer**: `@Cacheable` skips method execution if the key exists in cache, whereas `@CachePut` always executes the method and updates the cache with the new return value.

??? question "Question 2: How does setting `sync = true` on `@Cacheable` mitigate Cache Stampede?"
    **Answer**: It locks the underlying cache lookup locally within the JVM, allowing only one thread to execute the database query while other concurrent threads wait for the cache to populate.

??? question "Question 3: Why is standard Java serialization discouraged for Redis caching in distributed microservices?"
    **Answer**: Standard Java serialization is unreadable by non-Java clients, brittle to class bytecode version changes, and carries notorious security deserialization vulnerabilities.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0051: Database Integration Testing with Testcontainers**](0051-database-integration-testing-testcontainers.md) | [**All Lessons**](index.md) | [ **0053: Redis Pub/Sub Messaging for Real-Time Event Fanout**](0053-redis-pub-sub-messaging.md) |

🎉 **Lesson 0052 completed! Proceed to Lesson 0053 to master real-time distributed messaging with Redis Pub/Sub.**
