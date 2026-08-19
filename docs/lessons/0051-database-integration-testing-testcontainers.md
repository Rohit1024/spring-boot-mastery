---
icon: lucide/database
---

# 0051: Database integration testing with Testcontainers

For years, developers used in-memory databases like **H2** for integration testing. While fast, H2 creates a dangerous **false sense of security**: H2 lacks PostgreSQL `JSONB` operators, spatial functions, window partition nuances, and concurrency isolation semantics. Code that passes on H2 frequently crashes in production PostgreSQL or MySQL environments.

**Testcontainers** provides genuine, lightweight, disposable instances of real databases running inside Docker containers for your test suite.

In this lesson, you will master configuring Testcontainers with Spring Boot, connecting repositories to real PostgreSQL containers using `@ServiceConnection` and `@DynamicPropertySource`, and sharing singleton containers across your test suite.

---

## 1. Testcontainers integration architecture

``` mermaid
flowchart TD
    subgraph TestExecution["JUnit 5 Test Suite"]
        DataJpaTest["@DataJpaTest / @SpringBootTest"]
    end

    subgraph SpringContext["Spring ApplicationContext"]
        HikariCP["HikariCP DataSource"]
        DynamicProps["@ServiceConnection / @DynamicPropertySource"]
        Repo["OrderRepository (Spring Data JPA)"]
        
        HikariCP --> Repo
        DynamicProps -->|Dynamically injects JDBC URL & Port| HikariCP
    end

    subgraph DockerDaemon["Docker Engine Daemon"]
        Ryuk["testcontainers/ryuk (Garbage Collector Container)"]
        PostgresContainer["postgres:16-alpine (Container on random port e.g. :54321)"]
        
        Ryuk -.->|Monitors & Auto-destroys on JVM exit| PostgresContainer
    end

    DataJpaTest --> SpringContext
    HikariCP -->|Real JDBC Connection over TCP| PostgresContainer
```

---

## 2. Maven dependencies (`pomxml`)

Add Testcontainers and Spring Boot's Testcontainers support dependencies:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-testcontainers</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>junit-jupiter</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>postgresql</artifactId>
    <scope>test</scope>
</dependency>
```

---

## 3. Modern database slicing with `@ServiceConnection`

Starting in **Spring Boot 3.1+**, `@ServiceConnection` completely eliminates verbose `@DynamicPropertySource` boilerplate. It automatically discovers the container's dynamic port and configures `spring.datasource.*` properties:

```java
package com.example.ecommerce.order;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.testcontainers.containers.PostgreSQLContainer;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

@DataJpaTest
@Testcontainers
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE) // Do NOT replace with H2!
class OrderRepositoryTest {

    @Container
    @ServiceConnection // Automatically wires JDBC URL, username, and password into Spring Boot!
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired
    private OrderRepository orderRepository;

    @Test
    @DisplayName("Should persist and find orders by customer ID in real PostgreSQL")
    void shouldPersistAndRetrieveOrders() {
        // Given
        Order order = new Order("CUST-100", new BigDecimal("199.99"), OrderStatus.COMPLETED);
        orderRepository.save(order);

        // When
        List<Order> found = orderRepository.findByCustomerId("CUST-100");

        // Then
        assertThat(found)
                .hasSize(1)
                .first()
                .satisfies(o -> {
                    assertThat(o.getId()).isNotNull();
                    assertThat(o.getTotalAmount()).isEqualByComparingTo(new BigDecimal("199.99"));
                    assertThat(o.getStatus()).isEqualTo(OrderStatus.COMPLETED);
                });
    }
}
```

---

## 4. Legacy pattern: `@DynamicPropertySource` (Spring Boot 30)

If you need custom connection parameters or use older Spring Boot 3.0 versions:

```java
@DynamicPropertySource
static void configureProperties(DynamicPropertyRegistry registry) {
    registry.add("spring.datasource.url", postgres::getJdbcUrl);
    registry.add("spring.datasource.username", postgres::getUsername);
    registry.add("spring.datasource.password", postgres::getPassword);
}
```

---

## 5. Reusable singleton containers pattern

Restarting Docker containers for every individual test class adds massive time overhead. By defining a **Singleton Abstract Base Class**, one PostgreSQL container is reused across your entire test suite:

```java
public abstract class AbstractIntegrationTest {

    static final PostgreSQLContainer<?> POSTGRES_CONTAINER;

    static {
        // Starts ONCE for the entire JVM test suite run:
        POSTGRES_CONTAINER = new PostgreSQLContainer<>("postgres:16-alpine")
                .withReuse(true);
        POSTGRES_CONTAINER.start();
    }

    @DynamicPropertySource
    static void dynamicProperties(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", POSTGRES_CONTAINER::getJdbcUrl);
        registry.add("spring.datasource.username", POSTGRES_CONTAINER::getUsername);
        registry.add("spring.datasource.password", POSTGRES_CONTAINER::getPassword);
    }
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4: Testcontainers evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Spring Boot 3.1+)"]
        ServiceConn3["@ServiceConnection Annotation Support"]
        DevServices3["Local Dev with Testcontainers @BootTest"]
        ManualFlyway["Flyway / Liquibase Migration verification in tests"]
    end

    subgraph SB4["Spring Boot 4.x (Native Cloud Test Suites)"]
        ZeroConfigServiceConn["Zero-Config Auto-Discovered @ServiceConnection"]
        NativeComposeDev["Unified Testcontainers + Docker Compose Dev Mode"]
        FastSnapshotRestore["Container State Snapshots for Sub-Second Test Restores"]
    end

    SB3 ==>|Snapshot State Restores & Auto-Discovered Service Connections| SB4
```

### Key differences and configuration comparison

| Testcontainers Aspect | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Container Wiring** | `@ServiceConnection` required explicit field annotations on static containers. | **Auto-Discovered Service Connections**: Auto-detects container types without manual annotations. |
| **Test Execution Speed** | Container startup took ~3-5s per container. | **Instant Snapshot Restoring**: Resets database state via instant Docker filesystem snapshots in under 100ms. |
| **Local Development** | Spring Boot Testcontainers Desktop dev mode. | **Unified DevServices**: Seamless sharing of container instances between `mvn spring-boot:run` and unit tests. |

---

## 7. Primary sources and further reading

- [Testcontainers Official Documentation](https://java.testcontainers.org/), Database containers, modules, and Docker lifecycle.
- [Spring Boot Testcontainers Reference](https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.testing.testcontainers), `@ServiceConnection` and Dynamic Property injection.

---

## 8. Knowledge check and practice

??? question "Question 1: Why is testing against real PostgreSQL using Testcontainers superior to using an in-memory H2 database?"
    **Answer**: In-memory H2 lacks native PostgreSQL capabilities (e.g. JSONB columns, exact constraint syntax, window partition dialects, and concurrency locking semantics), hiding bugs that emerge in production.

??? question "Question 2: What is the purpose of `@ServiceConnection` in Spring Boot 3.1+?"
    **Answer**: It automatically detects the container type (such as `PostgreSQLContainer`) and dynamically injects the connection URL, username, and password into Spring Boot's DataSource configuration without writing `@DynamicPropertySource` boilerplate.

??? question "Question 3: How does the Singleton Container pattern prevent slow test execution?"
    **Answer**: By starting a single static Docker container instance in a shared base class that remains running across all test classes, eliminating repetitive container spin-up and teardown overhead.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0050: REST API Testing with MockMvc**](0050-integration-testing-rest-apis-mockmvc.md) | [**All Lessons**](index.md) | [ **0052: Spring Cache Abstraction with Redis**](0052-spring-cache-abstraction-redis.md) |

🎉 **Congratulations on completing Module 11: Enterprise Testing & Quality Assurance!**
