---
icon: lucide/database
---

# 0075: Non-blocking persistence with R2DBC and Reactive Redis

For years, building end-to-end reactive microservices with relational databases was impossible because the **Java Database Connectivity (JDBC)** standard was designed around blocking socket I/O. Using Hibernate or standard JPA in a WebFlux app blocks Netty event loop threads and destroys system concurrency.

**R2DBC (Reactive Relational Database Connectivity)** is an open specification that brings non-blocking, reactive streams to relational databases (PostgreSQL, MySQL, MariaDB, SQL Server). Combined with **`ReactiveRedisTemplate`**, you can build 100% non-blocking data pipelines from the network socket down to disk and cache.

In this lesson, you will master Spring Data R2DBC repositories, programmatic querying with `DatabaseClient`, reactive transaction management with `TransactionalOperator`, and caching with `ReactiveRedisTemplate`.

---

## 1. End-to-end non-blocking data pipeline architecture

``` mermaid
flowchart TD
    subgraph WebFluxTier["Spring WebFlux API Layer"]
        Controller["ProductReactiveController"]
        Service["ProductReactiveService"]
        Controller --> Service
    end

    subgraph ReactiveDataTier["Non-Blocking Persistence Layer"]
        ReactiveRedis["ReactiveRedisTemplate (Lettuce Reactive Driver)"]
        R2dbcRepo["ProductR2dbcRepository (Spring Data R2DBC)"]
        DbClient["DatabaseClient (Fluent Reactive SQL)"]
        TxOp["TransactionalOperator (Reactive Transactions)"]
    end

    subgraph DataStores["In-Memory & Relational Engines"]
        RedisStore[("Redis Server (RAM)")]
        PostgresDB[("PostgreSQL Database (r2dbc:postgresql://)")]
    end

    Service --> ReactiveRedis
    ReactiveRedis -->|1. Non-blocking GET| RedisStore

    Service -.->|2. Cache Miss: Query R2DBC| R2dbcRepo
    Service -.->|2. Complex Query: DatabaseClient| DbClient
    
    R2dbcRepo --> PostgresDB
    DbClient --> PostgresDB
    TxOp -.->|Manages non-blocking commit/rollback| PostgresDB
```

---

## 2. Maven dependencies (`pomxml`)

Include Spring Data R2DBC, PostgreSQL R2DBC driver, and Reactive Redis:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-r2dbc</artifactId>
</dependency>
<dependency>
    <groupId>org.postgresql</groupId>
    <artifactId>r2dbc-postgresql</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis-reactive</artifactId>
</dependency>
```

### Configuration (`applicationyml`)

```yaml
spring:
  r2dbc:
    url: r2dbc:postgresql://localhost:5432/reactive_db
    username: postgres
    password: secretpassword
    pool:
      enabled: true
      initial-size: 10
      max-size: 30
      max-idle-time: 30m

  data:
    redis:
      host: localhost
      port: 6379
```

---

## 3. R2DBC entity reactive repository

> [!NOTE]
> **R2DBC vs JPA**: R2DBC entities do **not** use JPA `@Entity` or Hibernate annotations. Use Spring Data's `@Table`, `@Id`, and `@Column` annotations. There is no lazy-loading or dirty checking in R2DBC.

```java
package com.example.model;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.data.annotation.Id;
import org.springframework.data.relational.core.mapping.Table;

import java.time.Instant;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Table("products")
public class Product {

    @Id
    private Long id;
    private String name;
    private double price;
    private String sku;
    private Instant createdAt;
}
```

### Reactive repository interface

```java
package com.example.repository;

import com.example.model.Product;
import org.springframework.data.r2dbc.repository.Query;
import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@Repository
public interface ProductR2dbcRepository extends R2dbcRepository<Product, Long> {

    Flux<Product> findByPriceGreaterThan(double price);

    @Query("SELECT * FROM products WHERE sku = :sku LIMIT 1")
    Mono<Product> findBySkuCustom(String sku);
}
```

---

## 4. Reactive caching with `ReactiveRedisTemplate`

Implement a pure reactive Cache-Aside pattern:

```java
package com.example.service;

import com.example.model.Product;
import com.example.repository.ProductR2dbcRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.ReactiveRedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.reactive.TransactionalOperator;
import reactor.core.publisher.Mono;

import java.time.Duration;

@Slf4j
@Service
@RequiredArgsConstructor
public class ProductReactiveService {

    private final ProductR2dbcRepository productRepository;
    private final ReactiveRedisTemplate<String, Product> reactiveRedisTemplate;
    private final TransactionalOperator transactionalOperator;

    /**
     * Pure Reactive Cache-Aside:
     * 1. Query Redis
     * 2. On Miss: Query R2DBC PostgreSQL
     * 3. Populate Redis asynchronously
     */
    public Mono<Product> getProductById(Long id) {
        String cacheKey = "product:" + id;

        return reactiveRedisTemplate.opsForValue().get(cacheKey)
                .doOnNext(cached -> log.info("Reactive Cache HIT for product: {}", id))
                .switchIfEmpty(
                        productRepository.findById(id)
                                .doOnNext(dbProduct -> log.info("Reactive Cache MISS. Fetched from R2DBC: {}", id))
                                .flatMap(dbProduct -> reactiveRedisTemplate.opsForValue()
                                        .set(cacheKey, dbProduct, Duration.ofMinutes(10))
                                        .thenReturn(dbProduct))
                );
    }

    /**
     * Reactive Transactional Write using TransactionalOperator
     */
    public Mono<Product> saveProductTransactional(Product product) {
        return productRepository.save(product)
                .flatMap(saved -> reactiveRedisTemplate.opsForValue()
                        .set("product:" + saved.getId(), saved, Duration.ofMinutes(10))
                        .thenReturn(saved))
                // Wraps the entire reactive sequence in a non-blocking database transaction
                .as(transactionalOperator::transactional);
    }
}
```

---

## 5. Dynamic queries with `DatabaseClient`

For complex dynamic filters or multi-table aggregations where derived queries are insufficient:

```java
package com.example.service;

import com.example.model.Product;
import lombok.RequiredArgsConstructor;
import org.springframework.r2dbc.core.DatabaseClient;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;

@Service
@RequiredArgsConstructor
public class ProductSearchService {

    private final DatabaseClient databaseClient;

    public Flux<Product> searchProducts(String nameKeyword, double minPrice) {
        return databaseClient.sql("""
                SELECT id, name, price, sku, created_at 
                FROM products 
                WHERE name ILIKE :name AND price >= :price 
                ORDER BY price ASC
                """)
                .bind("name", "%" + nameKeyword + "%")
                .bind("price", minPrice)
                .map((row, metadata) -> Product.builder()
                        .id(row.get("id", Long.class))
                        .name(row.get("name", String.class))
                        .price(row.get("price", Double.class))
                        .sku(row.get("sku", String.class))
                        .createdAt(row.get("created_at", java.time.Instant.class))
                        .build())
                .all();
    }
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **R2DBC Connection Pooling** | `r2dbc-pool` managing reactive connection lifecycles. | Native connection multiplexing and zero-copy packet parsers. |
| **Transaction Management** | `TransactionalOperator` and `@Transactional` via `ReactiveTransactionManager`. | Unified reactive and virtual-thread transaction scope coordinators. |
| **Schema Migration** | Flyway/Liquibase require separate JDBC dependency to run migrations at startup. | First-class native R2DBC asynchronous database schema migration runners. |

---

## 7. Primary sources and further reading

- [R2DBC Official Specification & Drivers](https://r2dbc.io/).
- [Spring Data R2DBC Reference Documentation](https://docs.spring.io/spring-data/r2dbc/reference/).
- [Spring Data Redis Reactive Support](https://docs.spring.io/spring-data/redis/reference/redis/reactive.html).

---

## 8. Knowledge check and practice

??? question "Question 1: Why cannot JPA/Hibernate be used directly inside a high-throughput Spring WebFlux application?"
    **Answer**: Because JPA is built on blocking JDBC APIs that block Netty event loop threads, rapidly starving worker threads and crashing throughput.

??? question "Question 2: How does `TransactionalOperator` manage transactions in a reactive pipeline?"
    **Answer**: It intercepts the reactive stream operators and coordinates non-blocking commit or rollback signals with the `ReactiveTransactionManager`.

??? question "Question 3: What is the purpose of `DatabaseClient` in Spring Data R2DBC?"
    **Answer**: It provides a fluent, non-blocking API to execute arbitrary SQL queries, bind parameters reactively, and map result rows directly into domain records.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0074: Building Reactive REST APIs with Spring WebFlux**](0074-building-reactive-rest-apis-spring-webflux.md) | [**All Lessons**](index.md) | [ **0076: Real-Time Streaming with Server-Sent Events (SSE)**](0076-realtime-streaming-server-sent-events-sse.md) |

🎉 **Lesson 0075 completed! Proceed to Lesson 0076 to master real-time live data streaming with Server-Sent Events (SSE).**
