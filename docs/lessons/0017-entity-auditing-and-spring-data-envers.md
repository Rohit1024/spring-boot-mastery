---
icon: lucide/history
---

# 0017: Entity Auditing with JPA & Historical Revision Tracking with Hibernate Envers

In enterprise and fintech applications, tracking **who changed what, and when** is not just an architectural best practice — it is a strict legal and regulatory compliance requirement (SOC 2, ISO 27001, HIPAA, GDPR).

In this lesson, you will implement automated entity auditing using **Spring Data JPA Auditing** (`@CreatedDate`, `@LastModifiedBy`, `AuditorAware`), capture full immutable historical deltas with **Hibernate Envers** (`@Audited`), and implement modern **Soft Deletes** in Hibernate 6.x.

---

## 1. JPA Auditing vs Hibernate Envers

Understanding the scope of both tools is critical for proper system design:

``` mermaid
flowchart TD
    subgraph JPAAudit["Spring Data JPA Auditing"]
        JPAField["Tracks Current Metadata Only<br/>(created_by, created_at,<br/>last_modified_by, last_modified_at)"]
    end

    subgraph Envers["Hibernate Envers"]
        ShadowTable["Captures Full Historical Delta Log<br/>(users_aud + revinfo shadow tables)<br/><i>Every single update preserved!</i>"]
    end

    JPAAudit ~~~ Envers
```

- **Spring Data JPA Auditing**: Captures *metadata for the current state* (overwriting previous modification stamps).
- **Hibernate Envers**: Captures *every historical version of the entity*, creating point-in-time revision logs that can be reconstructed historically.

---

## 2. Setting Up Spring Data JPA Auditing

### Step 1: Create a Reusable Auditable Base Entity

```java
package com.example.demo.domain;

import jakarta.persistence.Column;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.MappedSuperclass;
import lombok.Getter;
import lombok.Setter;
import org.springframework.data.annotation.CreatedBy;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedBy;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import java.time.Instant;

@MappedSuperclass
@EntityListeners(AuditingEntityListener.class)
@Getter
@Setter
public abstract class AuditableBaseEntity {

    @CreatedBy
    @Column(name = "created_by", nullable = false, updatable = false)
    private String createdBy;

    @CreatedDate
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @LastModifiedBy
    @Column(name = "last_modified_by")
    private String lastModifiedBy;

    @LastModifiedDate
    @Column(name = "last_modified_at")
    private Instant lastModifiedAt;
}
```

---

### Step 2: Implement `AuditorAware` (Integrating with Spring Security)

Spring Data needs to know who the "current user" is. We resolve this from the `SecurityContext`:

```java
package com.example.demo.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.domain.AuditorAware;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;

import java.util.Optional;

@Configuration
@EnableJpaAuditing(auditorAwareRef = "auditorProvider")
public class JpaAuditingConfig {

    @Bean
    public AuditorAware<String> auditorProvider() {
        return () -> {
            Authentication auth = SecurityContextHolder.getContext().getAuthentication();
            if (auth == null || !auth.isAuthenticated() || "anonymousUser".equals(auth.getPrincipal())) {
                return Optional.of("SYSTEM");
            }
            return Optional.of(auth.getName());
        };
    }
}
```

---

## 3. Historical Versioning with Hibernate Envers

When an entity is annotated with `@Audited`, Hibernate Envers automatically provisions shadow audit tables (`orders_aud` and `revinfo`) to track every revision.

``` mermaid
sequenceDiagram
    autonumber
    actor Service as OrderService
    participant Hibernate as Hibernate Envers
    participant DB as PostgreSQL

    Service->>Hibernate: order.setStatus(SHIPPED) (Commit TX)
    Hibernate->>DB: 1. UPDATE orders SET status = 'SHIPPED' WHERE id = 101
    Hibernate->>DB: 2. INSERT INTO revinfo (rev, revtstmp) VALUES (42, 1723850000)
    Hibernate->>DB: 3. INSERT INTO orders_aud (id, rev, revtype, status, amount) VALUES (101, 42, 1, 'SHIPPED', 250.00)
    Note over DB: revtype: 0 (ADD), 1 (MOD), 2 (DEL)
```

### Entity with Hibernate Envers

```java
package com.example.demo.domain;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.envers.Audited;

import java.math.BigDecimal;

@Entity
@Table(name = "orders")
@Audited // ✅ Envers tracks all mutations to this entity
@Getter @Setter @NoArgsConstructor
public class Order extends AuditableBaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String orderNumber;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private OrderStatus status;

    @Column(nullable = false)
    private BigDecimal totalAmount;
}
```

---

## 4. Querying Historical Revisions with `AuditReader`

You can query the exact state of an entity at any historical revision or timestamp using `AuditReader`:

```java
package com.example.demo.service;

import com.example.demo.domain.Order;
import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import org.hibernate.envers.AuditReader;
import org.hibernate.envers.AuditReaderFactory;
import org.hibernate.envers.query.AuditEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class OrderHistoryService {

    @PersistenceContext
    private EntityManager entityManager;

    @Transactional(readOnly = true)
    public Order getOrderAtRevision(Long orderId, Number revisionNumber) {
        AuditReader auditReader = AuditReaderFactory.get(entityManager);
        // Fetches entity state exactly as it existed at revisionNumber!
        return auditReader.find(Order.class, orderId, revisionNumber);
    }

    @Transactional(readOnly = true)
    @SuppressWarnings("unchecked")
    public List<Number> getRevisionsForOrder(Long orderId) {
        AuditReader auditReader = AuditReaderFactory.get(entityManager);
        return auditReader.getRevisions(Order.class, orderId);
    }
}
```

---

## 5. Modern Soft Deletes in Hibernate 6.x

In enterprise systems, physical `DELETE` statements are often forbidden. Hibernate 6.x provides `@SQLDelete` and `@SQLRestriction`:

```java
@Entity
@Table(name = "users")
@SQLDelete(sql = "UPDATE users SET deleted = true WHERE id = ?")
@SQLRestriction("deleted = false") // Replaces legacy @Where in Hibernate 6.x
@Getter @Setter @NoArgsConstructor
public class User extends AuditableBaseEntity {

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String email;

    @Column(nullable = false)
    private boolean deleted = Boolean.FALSE;
}
```
- Calling `userRepository.deleteById(1L)` executes `UPDATE users SET deleted = true WHERE id = 1`.
- Any subsequent `userRepository.findAll()` or `userRepository.findById(1L)` automatically includes `AND deleted = false`.

---

## 6. Spring Boot 3 vs Spring Boot 4: Auditing & Temporal Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        EnversShadow["Envers Shadow _AUD Tables"]
        AuditorAwareBean["AuditorAware<String> Security Context Bridge"]
        SQLRestriction6["@SQLRestriction Annotations for Soft Deletes"]
    end

    subgraph SB4["Spring Boot 4.x"]
        TemporalTables["Native SQL:2011 Temporal Versioning"]
        OTelAuditBridge["Automated OTel Trace/Span Context Auditing"]
        StatelessEnvers["High-Throughput Stateless Audit Pipeline"]
    end

    SB3 ==>|Audit & Compliance Modernization| SB4
```

### Key Differences & Configuration Comparison

| Auditing Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Historical Versioning** | Relied on application-managed shadow `_AUD` tables via Envers triggers. | **Native Temporal Tables (SQL:2011)**: Integrates with database-native temporal table features (`AS OF SYSTEM TIME`). |
| **Audit Context Enrichment** | Limited to username / principal extracted via `AuditorAware`. | **Distributed Context Auditing**: Automatically binds active W3C `traceId`, `spanId`, and client tenant into audit entities. |
| **Soft Delete Annotations** | Hibernate 6 `@SQLDelete` and `@SQLRestriction`. | **Declarative `@SoftDelete` Annotation**: Built-in first-class soft delete annotation in Hibernate 7 / Jakarta Persistence 3.2. |

---

## 7. Primary Sources & Further Reading

- [Spring Data JPA: Auditing](https://docs.spring.io/spring-data/jpa/reference/auditing.html) — Configuring `AuditingEntityListener` and `AuditorAware`.
- [Hibernate Envers User Guide](https://docs.jboss.org/hibernate/orm/current/userguide/html_single/Hibernate_User_Guide.html#envers) — Revision tables, metadata, and `AuditReader` queries.
- [Vlad Mihalcea: How to Audit Entities with Hibernate Envers](https://vladmihalcea.com/hibernate-envers-audit-log-entity-change/) — Best practices for enterprise change logging.

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the key difference between Spring Data JPA Auditing and Hibernate Envers?"
    **Answer**: Spring Data JPA Auditing only maintains the current modification timestamps and actor, while Hibernate Envers captures full immutable revision deltas in shadow audit tables for every update.

??? question "Question 2: What are the three Envers revision types recorded in the shadow `_AUD` tables?"
    **Answer**: `0` represents ADD (Insert), `1` represents MOD (Update), and `2` represents DEL (Delete).

??? question "Question 3: In Hibernate 6.x / Spring Boot 3.x, what annotation replaces `@Where(clause = ...)` for filtering soft-deleted rows?"
    **Answer**: `@SQLRestriction("deleted = false")` is the modern Hibernate 6 annotation that replaces the deprecated `@Where` annotation.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0016: Multi-DataSource & NoSQL Integration**](0016-multi-datasource-and-nosql-integration.md) | [**All Lessons**](index.md) | [➡️ **0018: Spring Boot DevTools & LiveReload**](0018-spring-boot-devtools-and-livereload.md) |

🎉 **Congratulations on completing Module 3: Persistence Mastery — Hibernate, JPA & R2DBC!**

