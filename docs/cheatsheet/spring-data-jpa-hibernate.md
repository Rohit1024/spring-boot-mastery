---
icon: lucide/database
---

# Spring Data JPA and Hibernate cheatsheet

Reference guide for JPA entity mappings, repository derived queries, fetch strategies, `@Transactional` configurations, and multi-database settings.

---

## 1. Entity lifecycle states and EntityManager

``` mermaid
stateDiagram-v2
    [*] --> TRANSIENT : new Entity()
    TRANSIENT --> MANAGED : em.persist(e) / repo.save(e)
    MANAGED --> DETACHED : em.detach(e) / em.clear()
    DETACHED --> MANAGED : em.merge(e)
    MANAGED --> REMOVED : em.remove(e)
    MANAGED --> [*] : commit & flush
```

| Method | Effect |
| :--- | :--- |
| `em.persist(e)` | Transitions `TRANSIENT` -> `MANAGED`. Entity receives generated database ID if configured. |
| `em.merge(e)` | Copies state of `DETACHED` entity into a new `MANAGED` entity instance. |
| `em.remove(e)` | Transitions `MANAGED` -> `REMOVED`. Queues SQL `DELETE` for next flush. |
| `em.detach(e)` | Removes entity from Persistence Context and stops dirty checking. |
| `em.flush()` | Forces pending SQL (`INSERT`, `UPDATE`, `DELETE`) to execute without committing. |
| `em.clear()` | Detaches all entities from the current Persistence Context. |

---

## 2. Common JPA entity annotations

```java
@Entity
@Table(name = "orders", indexes = {
    @Index(name = "idx_order_customer", columnList = "customer_id"),
    @Index(name = "idx_order_status", columnList = "status")
})
@Getter @Setter @NoArgsConstructor
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_number", nullable = false, unique = true, length = 64)
    private String orderNumber;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 32)
    private OrderStatus status;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "customer_id", nullable = false)
    private Customer customer;

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<OrderItem> items = new ArrayList<>();

    @Version
    private Long version; // Optimistic locking
}
```

---

## 3. Spring Data derived query reference

| Keyword | Repository method signature | Derived JPQL snippet |
| :--- | :--- | :--- |
| `And` | `findByStatusAndCustomerId(...)` | `WHERE o.status = :status AND o.customerId = :cId` |
| `Or` | `findByNameOrEmail(...)` | `WHERE u.name = :name OR u.email = :email` |
| `Between` | `findByCreatedAtBetween(Instant s, Instant e)` | `WHERE o.createdAt BETWEEN :s AND :e` |
| `LessThan` / `GreaterThan` | `findByAgeGreaterThanEqual(int age)` | `WHERE u.age >= :age` |
| `Like` / `Containing` | `findByNameContainingIgnoreCase(String q)` | `WHERE LOWER(u.name) LIKE %:q%` |
| `In` | `findByStatusIn(Collection<Status> statuses)` | `WHERE o.status IN (:statuses)` |
| `True` / `False` | `findByActiveTrue()` | `WHERE u.active = true` |
| `OrderBy` | `findByCategoryOrderByPriceDesc(...)` | `WHERE p.category = :c ORDER BY p.price DESC` |
| `Top` / `First` | `findTop10ByOrderByScoreDesc()` | `ORDER BY s.score DESC LIMIT 10` |
| `Exists` | `boolean existsByEmail(String email)` | `SELECT count(u) > 0 WHERE u.email = :email` |
| `Count` | `long countByStatus(OrderStatus status)` | `SELECT count(o) WHERE o.status = :status` |

---

## 4. Query types: JPQL, native SQL, and projections

```java
public interface UserRepository extends JpaRepository<User, Long> {

    // 1. JPQL
    @Query("SELECT u FROM User u WHERE u.email = :email")
    Optional<User> findByEmailJpql(@Param("email") String email);

    // 2. Native SQL (PostgreSQL specific)
    @Query(value = "SELECT * FROM users WHERE metadata->>'tier' = 'GOLD'", nativeQuery = true)
    List<User> findGoldTierUsers();

    // 3. Record DTO projection
    @Query("SELECT new com.example.dto.UserSummaryDto(u.id, u.email) FROM User u")
    List<UserSummaryDto> findAllSummaries();

    // 4. JOIN FETCH to eliminate N+1 queries
    @Query("SELECT o FROM Order o JOIN FETCH o.customer WHERE o.id = :id")
    Optional<Order> findWithCustomerById(@Param("id") Long id);

    // 5. Spring @EntityGraph
    @EntityGraph(attributePaths = {"customer", "items"})
    List<Order> findByStatus(OrderStatus status);
}
```

---

## 5. `@Transactional` propagation and isolation reference

### Propagation
- **`REQUIRED`** *(Default)*: Joins existing transaction or creates a new one.
- **`REQUIRES_NEW`**: Starts an independent transaction and suspends the existing one.
- **`NESTED`**: Executes within a nested transaction using JDBC savepoints.
- **`MANDATORY`**: Requires an existing transaction; throws an exception if none exists.
- **`SUPPORTS`**: Runs in a transaction if present; executes non-transactionally otherwise.

### Isolation levels
- **`READ_COMMITTED`**: Standard default for PostgreSQL and Oracle. Prevents dirty reads.
- **`REPEATABLE_READ`**: Standard default for MySQL InnoDB. Prevents dirty and non-repeatable reads.
- **`SERIALIZABLE`**: Highest isolation. Prevents all concurrency anomalies through strict row and range locks.

---

## Navigation and cheatsheet index

| Previous | Cheatsheet index | Next |
| :--- | :---: | ---: |
| [**Spring Web MVC and REST APIs cheatsheet**](spring-web-mvc-rest.md) | [**All cheatsheets**](index.md) | [**Spring observability, Actuator, and logging cheatsheet**](spring-observability-devtools.md) |
