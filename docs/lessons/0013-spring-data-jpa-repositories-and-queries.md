---
icon: lucide/layers
---

# 0013: Spring Data JPA: Repositories, Derived Query Methods, Pagination & JPQL vs Native Queries

Writing raw JPQL or managing `EntityManager` transactions for basic CRUD operations quickly becomes repetitive. **Spring Data JPA** eliminates this boilerplate by providing runtime repository proxy generation, derived query parsing, and powerful pagination abstractions.

In this lesson, you will master the repository hierarchy, derived query method semantics, the performance trade-offs between **JPQL** and **Native SQL**, and the critical difference between `Page<T>` and `Slice<T>`.

---

## 1. The Spring Data Repository Hierarchy

Spring Data JPA provides a structured hierarchy of generic repository interfaces. Understanding this hierarchy allows you to choose the most focused abstraction for your domain needs:

``` mermaid
classDiagram
    class Repository~T, ID~ {
        <<Marker Interface>>
    }
    class CrudRepository~T, ID~ {
        +save(entity)
        +findById(id)
        +existsById(id)
        +findAll()
        +deleteById(id)
    }
    class ListCrudRepository~T, ID~ {
        +findAll() List~T~
        +saveAll() List~T~
    }
    class PagingAndSortingRepository~T, ID~ {
        +findAll(Sort)
        +findAll(Pageable)
    }
    class JpaRepository~T, ID~ {
        +flush()
        +saveAndFlush(entity)
        +deleteAllInBatch()
        +getReferenceById(id)
    }

    Repository <|-- CrudRepository
    CrudRepository <|-- ListCrudRepository
    Repository <|-- PagingAndSortingRepository
    ListCrudRepository <|-- JpaRepository
    PagingAndSortingRepository <|-- JpaRepository
```

### How Spring Data Creates Repositories Under the Hood

When your application starts up:
1. Spring Data scans for interfaces extending `Repository`.
2. It generates a dynamic Java proxy implementing your interface.
3. The default target implementation delegating to `EntityManager` is `SimpleJpaRepository<T, ID>`.

``` mermaid
sequenceDiagram
    autonumber
    actor Service as UserService
    participant Proxy as JpaRepository Dynamic Proxy
    participant Impl as SimpleJpaRepository
    participant EM as EntityManager / Hibernate
    participant DB as PostgreSQL

    Service->>Proxy: userRepository.findById(101L)
    Proxy->>Impl: Delegates method call
    Impl->>EM: em.find(User.class, 101L)
    EM->>DB: SELECT * FROM users WHERE id = 101
    DB-->>EM: User Record
    EM-->>Impl: Managed User Entity
    Impl-->>Service: Optional<User>
```

---

## 2. Derived Query Methods: Magic from Method Names

Spring Data JPA contains a query generation parser that inspects repository method names and automatically derives the corresponding JPQL query at application startup.

### Query Keyword Vocabulary:

```java
public interface UserRepository extends JpaRepository<User, Long> {

    // Exact equality match: WHERE u.email = :email
    Optional<User> findByEmail(String email);

    // Multiple criteria: WHERE u.lastName = :lastName AND u.status = :status
    List<User> findByLastNameAndStatus(String lastName, UserStatus status);

    // Case-insensitive lookups: WHERE LOWER(u.username) = LOWER(:username)
    Optional<User> findByUsernameIgnoreCase(String username);

    // Substring searches: WHERE u.fullName LIKE %:prefix%
    List<User> findByFullNameContaining(String keyword);

    // Range queries: WHERE u.createdAt BETWEEN :start AND :end
    List<User> findByCreatedAtBetween(Instant start, Instant end);

    // Existence checks: SELECT count(u) > 0 WHERE u.email = :email
    boolean existsByEmail(String email);

    // Limiting results: Top / First
    List<User> findTop5ByOrderByCreatedAtDesc();
}
```

!!! note "Startup Verification"
    Spring Data validates all derived query method names during **application context startup**. If you misspell a field name (e.g., `findByEmaill`), Spring Boot fails to start immediately with a descriptive `PropertyReferenceException`, preventing runtime SQL surprises!

---

## 3. JPQL vs Native SQL: When to Use Which

When derived methods cannot express complex joins, aggregations, or subqueries, use the `@Query` annotation.

``` mermaid
flowchart TD
    QType{"Need custom query?"}
    QType -->|Object-oriented, DB-agnostic| JPQL["✍️ JPQL Query<br/>Operates on Entity classes & fields"]
    QType -->|DB-specific features: JSONB, CTEs, Window functions| Native["⚡ Native SQL<br/><code>nativeQuery = true</code>"]
```

### JPQL (Jakarta Persistence Query Language)

JPQL operates on **Java entity objects and attributes**, not database tables and columns:

```java
@Query("SELECT u FROM User u WHERE u.status = :status AND u.failedLoginAttempts >= :threshold")
List<User> findSuspiciousUsers(@Param("status") UserStatus status, 
                              @Param("threshold") int threshold);
```

- **Pros**: Portable across database dialects (Postgres, MySQL, Oracle); type-checked against entity model.
- **Cons**: Cannot access proprietary database functions directly without custom dialect registration.

### Native SQL Queries

Native queries execute raw SQL directly against the underlying database engine:

```java
@Query(value = """
       SELECT u.* FROM users u 
       JOIN user_preferences p ON u.id = p.user_id 
       WHERE p.settings->>'theme' = 'DARK' 
       AND u.created_at >= NOW() - INTERVAL '30 days'
       """, nativeQuery = true)
List<User> findRecentDarkModeUsers();
```

- **Pros**: Full access to database-specific capabilities (PostgreSQL JSONB operators `->>`, Common Table Expressions `WITH`, window functions `ROW_NUMBER() OVER()`).
- **Cons**: Ties your code to a specific database engine; syntax errors only surface when the query executes.

---

## 4. High-Performance Pagination: `Page<T>` vs `Slice<T>`

When querying large datasets, you must never return unpaginated lists. Spring Data JPA provides `Pageable` and two distinct return abstractions: `Page<T>` and `Slice<T>`.

```java
public interface ProductRepository extends JpaRepository<Product, Long> {
    Page<Product> findByCategory(String category, Pageable pageable);
    Slice<Product> findByStatus(ProductStatus status, Pageable pageable);
}
```

### The Architectural Difference:

| Feature | `Page<T>` | `Slice<T>` |
| :--- | :--- | :--- |
| **SQL Executed** | `SELECT ... LIMIT X OFFSET Y` <br/>**PLUS** `SELECT COUNT(*) FROM ...` | `SELECT ... LIMIT (X + 1) OFFSET Y` (No count query!) |
| **Total Pages / Items** | ✅ `getTotalElements()`, `getTotalPages()` | ❌ Unknown |
| **Has Next Page?** | ✅ `hasNext()` | ✅ `hasNext()` |
| **Ideal Use Case** | Classic desktop pagination with page numbers (`1, 2, 3... 45`) | Infinite scroll, mobile apps, high-throughput microservices |

``` mermaid
sequenceDiagram
    autonumber
    participant App as Service
    participant Repo as ProductRepository
    participant DB as PostgreSQL

    Note over App,DB: Scenario A: Page<Product> Request (Expensive)
    App->>Repo: repo.findByCategory("Electronics", PageRequest.of(0, 20))
    Repo->>DB: 1. SELECT * FROM products WHERE category = 'Electronics' LIMIT 20 OFFSET 0
    Repo->>DB: 2. SELECT COUNT(*) FROM products WHERE category = 'Electronics' (Expensive Table Scan!)
    DB-->>App: Returns Page (Data + Total Count 1,420,500)

    Note over App,DB: Scenario B: Slice<Product> Request (Lightweight & Fast)
    App->>Repo: repo.findByStatus(ACTIVE, PageRequest.of(0, 20))
    Repo->>DB: SELECT * FROM products WHERE status = 'ACTIVE' LIMIT 21 OFFSET 0
    Note over Repo: Fetches 21 rows. If 21 rows return,<br/>hasNext() is TRUE. Discards 21st item.
    DB-->>App: Returns Slice (Data + hasNext: true)
```

!!! tip "Performance Golden Rule: Prefer `Slice<T>` for Infinite Scrolling"
    In multi-million row tables, `SELECT COUNT(*)` can take hundreds of milliseconds or even seconds due to MVCC table scans. For infinite scrolling feeds or batch job processing, always use `Slice<T>` to completely eliminate the `COUNT(*)` overhead.

---

## 5. High-Efficiency Projections: Record-Based DTOs

Fetching complete entities when you only need a few columns wastes memory, CPU serialization time, and network bandwidth.

```java
// 1. Define lightweight Java Record DTO
public record UserSummaryDto(Long id, String email, String fullName) {}

// 2. Repository with JPQL Constructor Expression
public interface UserRepository extends JpaRepository<User, Long> {

    @Query("""
           SELECT new com.example.demo.dto.UserSummaryDto(u.id, u.email, u.fullName) 
           FROM User u 
           WHERE u.status = 'ACTIVE'
           """)
    List<UserSummaryDto> findAllActiveUserSummaries();
}
```

- Hibernate bypasses entity lifecycle tracking and dirty-checking snapshot creation.
- The SQL query only selects the 3 requested columns (`SELECT id, email, full_name ...`), drastically shrinking network payloads.

---

## 6. Primary Sources & Further Reading

- [Spring Data JPA Official Reference Documentation](https://docs.spring.io/spring-data/jpa/reference/) — Authoritative guide for repository query methods, projections, and paging.
- [Spring Data Common: Query Methods](https://docs.spring.io/spring-data/commons/reference/repositories/query-methods.html) — Query creation keywords and syntax tree.
- [Vlad Mihalcea: The Best Way to Map a DTO Projection](https://vladmihalcea.com/the-best-way-to-map-a-projection-query-to-a-dto-with-jpa-and-hibernate/) — Performance benchmarks comparing projections.

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: Why does `Slice<T>` query for `pageSize + 1` elements instead of running a `COUNT(*)` query?"
    **Answer**: By requesting one extra row (`limit + 1`), Spring Data checks if another page exists (`hasNext()`) without incurring the heavy performance penalty of a full database `COUNT(*)` scan.

??? question "Question 2: What is the primary difference between a derived query and a `@Query(nativeQuery = true)` query?"
    **Answer**: Derived queries generate database-independent JPQL validated at application startup against entities, whereas native queries execute raw, database-specific SQL strings directly against the database engine.

??? question "Question 3: Why are Java Record constructor DTO projections faster than returning full JPA entities?"
    **Answer**: Projections fetch only the selected columns from the database, do not instantiate complete entity graphs, and avoid persistence context dirty-checking snapshot tracking overhead.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0012: JDBC vs Hibernate ORM Internals**](0012-jdbc-vs-hibernate-orm-internals.md) | [**All Lessons**](index.md) | [➡️ **0014: Entity Relationships, Lazy Loading & N+1 Problem**](0014-entity-relationships-lazy-loading-n-plus-1.md) |
