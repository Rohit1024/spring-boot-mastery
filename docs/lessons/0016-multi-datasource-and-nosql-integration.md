---
icon: lucide/database-zap
---

# 0016: Multi-DataSource Architecture & NoSQL Integration (PostgreSQL + MySQL + MongoDB)

Modern enterprise architectures rarely rely on a single database engine. Real-world systems frequently adopt **Polyglot Persistence** — persisting core transactional ledger records in PostgreSQL, querying analytics/reporting from MySQL replicas, and ingesting high-throughput unstructured event payloads into MongoDB.

In this lesson, you will configure **Multiple Relational DataSources** in Spring Boot 3.x, implement **Dynamic Read/Write Replica Routing** with `AbstractRoutingDataSource`, and seamlessly integrate **Spring Data MongoDB** alongside JPA.

---

## 1. Polyglot Persistence Architecture

``` mermaid
flowchart TD
    App["🚀 Spring Boot 3.x Application"]
    
    subgraph JPA_RDBMS["Relational Persistence Layer (JPA / Hibernate)"]
        DS1["Primary DataSource<br/>(PostgreSQL - Orders & Users)"]
        DS2["Secondary DataSource<br/>(MySQL - Legacy Billing Data)"]
    end
    
    subgraph Mongo_NoSQL["Document Persistence Layer (Spring Data MongoDB)"]
        MongoDS["MongoDB Cluster<br/>(Audit Events & Telemetry Docs)"]
    end

    App -->|"@EnableJpaRepositories (primary)"| DS1
    App -->|"@EnableJpaRepositories (secondary)"| DS2
    App -->|"@EnableMongoRepositories"| MongoDS

    JPA_RDBMS ~~~ Mongo_NoSQL
```

---

## 2. Configuring Multiple Relational DataSources

When you define more than one DataSource, Spring Boot disables its automatic DataSource configuration. You must explicitly configure:
1. `DataSource` (HikariCP pool)
2. `EntityManagerFactory` (`LocalContainerEntityManagerFactoryBean`)
3. `PlatformTransactionManager` (`JpaTransactionManager`)

### `application.yml`
```yaml
spring:
  datasource:
    primary:
      jdbc-url: jdbc:postgresql://localhost:5432/primary_db
      username: postgres
      password: secretpassword
      driver-class-name: org.postgresql.Driver
    secondary:
      jdbc-url: jdbc:mysql://localhost:3306/billing_db
      username: mysql_user
      password: secretpassword
      driver-class-name: com.mysql.cj.jdbc.Driver
  data:
    mongodb:
      uri: mongodb://localhost:27017/telemetry_db
```

---

### Step 1: Configure Primary DataSource (PostgreSQL)

```java
package com.example.demo.config;

import jakarta.persistence.EntityManagerFactory;
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.orm.jpa.EntityManagerFactoryBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.transaction.PlatformTransactionManager;

import javax.sql.DataSource;

@Configuration
@EnableJpaRepositories(
    basePackages = "com.example.demo.repository.primary",
    entityManagerFactoryRef = "primaryEntityManagerFactory",
    transactionManagerRef = "primaryTransactionManager"
)
public class PrimaryDataSourceConfig {

    @Primary
    @Bean
    @ConfigurationProperties("spring.datasource.primary")
    public DataSourceProperties primaryDataSourceProperties() {
        return new DataSourceProperties();
    }

    @Primary
    @Bean
    public DataSource primaryDataSource() {
        return primaryDataSourceProperties()
                .initializeDataSourceBuilder()
                .build();
    }

    @Primary
    @Bean
    public LocalContainerEntityManagerFactoryBean primaryEntityManagerFactory(
            EntityManagerFactoryBuilder builder) {
        return builder
                .dataSource(primaryDataSource())
                .packages("com.example.demo.domain.primary")
                .persistenceUnit("primaryPU")
                .build();
    }

    @Primary
    @Bean
    public PlatformTransactionManager primaryTransactionManager(
            EntityManagerFactory primaryEntityManagerFactory) {
        return new JpaTransactionManager(primaryEntityManagerFactory);
    }
}
```

---

### Step 2: Configure Secondary DataSource (MySQL)

```java
package com.example.demo.config;

import jakarta.persistence.EntityManagerFactory;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.boot.autoconfigure.jdbc.DataSourceProperties;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.orm.jpa.EntityManagerFactoryBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.orm.jpa.JpaTransactionManager;
import org.springframework.orm.jpa.LocalContainerEntityManagerFactoryBean;
import org.springframework.transaction.PlatformTransactionManager;

import javax.sql.DataSource;

@Configuration
@EnableJpaRepositories(
    basePackages = "com.example.demo.repository.secondary",
    entityManagerFactoryRef = "secondaryEntityManagerFactory",
    transactionManagerRef = "secondaryTransactionManager"
)
public class SecondaryDataSourceConfig {

    @Bean
    @ConfigurationProperties("spring.datasource.secondary")
    public DataSourceProperties secondaryDataSourceProperties() {
        return new DataSourceProperties();
    }

    @Bean
    public DataSource secondaryDataSource() {
        return secondaryDataSourceProperties()
                .initializeDataSourceBuilder()
                .build();
    }

    @Bean
    public LocalContainerEntityManagerFactoryBean secondaryEntityManagerFactory(
            EntityManagerFactoryBuilder builder,
            @Qualifier("secondaryDataSource") DataSource dataSource) {
        return builder
                .dataSource(dataSource)
                .packages("com.example.demo.domain.secondary")
                .persistenceUnit("secondaryPU")
                .build();
    }

    @Bean
    public PlatformTransactionManager secondaryTransactionManager(
            @Qualifier("secondaryEntityManagerFactory") EntityManagerFactory secondaryEMF) {
        return new JpaTransactionManager(secondaryEMF);
    }
}
```

---

## 3. Dynamic Read/Write Replica Routing (`AbstractRoutingDataSource`)

In high-scale architectures with master-replica database clusters, write mutations must go to the **Master (Writer)** database, while read-only transactions can be routed to **Read Replicas (Readers)**:

``` mermaid
sequenceDiagram
    autonumber
    actor Client as OrderService
    participant Router as DynamicRoutingDataSource (AbstractRoutingDataSource)
    participant MasterDB as PostgreSQL (Master - RW)
    participant ReplicaDB as PostgreSQL (Replica - Read Only)

    alt @Transactional(readOnly = false)
        Client->>Router: determineCurrentLookupKey() -> "WRITE"
        Router->>MasterDB: INSERT INTO orders ...
    else @Transactional(readOnly = true)
        Client->>Router: determineCurrentLookupKey() -> "READ"
        Router->>ReplicaDB: SELECT * FROM orders ...
    end
```

### Implementing `AbstractRoutingDataSource`

```java
package com.example.demo.routing;

import org.springframework.jdbc.datasource.lookup.AbstractRoutingDataSource;
import org.springframework.transaction.support.TransactionSynchronizationManager;

public class TransactionRoutingDataSource extends AbstractRoutingDataSource {

    public enum DataSourceType { READ, WRITE }

    @Override
    protected Object determineCurrentLookupKey() {
        // Automatically inspects if Spring transaction is read-only!
        boolean isReadOnly = TransactionSynchronizationManager.isCurrentTransactionReadOnly();
        return isReadOnly ? DataSourceType.READ : DataSourceType.WRITE;
    }
}
```

---

## 4. Coexisting with NoSQL: Spring Data MongoDB

When combining relational JPA with MongoDB, Spring Boot allows both repository types to run side-by-side seamlessly.

### MongoDB Document Definition:

```java
package com.example.demo.document;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
import java.time.Instant;
import java.util.Map;

@Document(collection = "audit_events")
public record AuditEventDocument(
    @Id String id,
    String eventType,
    String userId,
    Map<String, Object> payload,
    Instant timestamp
) {}
```

### MongoDB Repository:

```java
package com.example.demo.repository.mongo;

import com.example.demo.document.AuditEventDocument;
import org.springframework.data.mongodb.repository.MongoRepository;
import java.util.List;

public interface AuditEventRepository extends MongoRepository<AuditEventDocument, String> {
    List<AuditEventDocument> findByUserId(String userId);
}
```

---

## 5. Spring Boot 3 vs Spring Boot 4: Multi-Database & Vector Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        ManualDataSources["Manual EMF & TxManager Boilerplate Beans"]
        RoutingThreadLocal["ThreadLocal Read/Write Routing"]
        TraditionalNoSQL["Standard Document & Key-Value NoSQL"]
    end

    subgraph SB4["Spring Boot 4.x"]
        DeclarativeMultiDB["Declarative Multi-Tenant & Multi-Source Config"]
        ScopedValRouting["ScopedValue Replica Lookup Engine"]
        NativeVectorStarters["Native AI Vector Store Starters (pgvector / Mongo Vector)"]
    end

    SB3 ==>|Polyglot Cloud Modernization| SB4
```

### Key Differences & Configuration Comparison

| Architecture Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Multi-DataSource Wiring** | Required ~60 lines of boilerplate `@Configuration` with explicit `EntityManagerFactoryBuilder`. | **Declarative Multi-DataSource Starters**: Simple profile and prefix-based automatic repository package binding. |
| **Read/Write Replica Routing** | Backed by `ThreadLocal` query inspect in `TransactionSynchronizationManager`. | **Loom-Native Scoped Routing**: High-throughput routing without thread pinning under Virtual Threads. |
| **Vector Database Integration** | Required third-party clients or manual JDBC SQL for embedding stores. | **First-Class Vector Repositories**: Integrated similarity search (`similaritySearch()`) via `spring-boot-starter-vector-pgvector`. |

---

## 6. Primary Sources & Further Reading

- [Spring Boot Reference: Two DataSources](https://docs.spring.io/spring-boot/reference/data/sql.html#data.sql.datasource.two-datasources) — Multi-datasource configuration guidelines.
- [Spring Data MongoDB Reference](https://docs.spring.io/spring-data/mongodb/reference/) — Complete documentation for MongoDB repositories and templates.
- [Baeldung: Dynamic Datasource Routing](https://www.baeldung.com/spring-abstract-routing-data-source) — Routing with `AbstractRoutingDataSource`.

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: Why does Spring Boot require explicit `EntityManagerFactory` and `TransactionManager` beans when configuring two DataSources?"
    **Answer**: Multiple DataSources cause Spring Boot's automatic single-datasource autoconfiguration to back off; explicit beans assign each repository package to its corresponding database and transaction manager.

??? question "Question 2: How does `AbstractRoutingDataSource` determine whether to route to a Read Replica vs a Write Master?"
    **Answer**: By inspecting `TransactionSynchronizationManager.isCurrentTransactionReadOnly()`, it selects the `READ` DataSource when `@Transactional(readOnly = true)` is active, and `WRITE` otherwise.

??? question "Question 3: Can JPA entities and MongoDB documents coexist in the same Spring Boot microservice?"
    **Answer**: Yes, Spring Data activates both `JpaRepositories` and `MongoRepositories` simultaneously by targeting distinct repository interfaces and document/entity models.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0015: Transaction Management & Propagation**](0015-transaction-management-and-propagation.md) | [**All Lessons**](index.md) | [➡️ **0017: Entity Auditing & Hibernate Envers**](0017-entity-auditing-and-spring-data-envers.md) |
