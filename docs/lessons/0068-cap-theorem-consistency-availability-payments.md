---
icon: lucide/triangle
---

# 0068: CAP Theorem in Action: Consistency vs Availability in Payment Systems

In distributed architecture, network failures, hardware crashes, and cross-datacenter packet drops are physical certainties.

Formulated by Eric Brewer, the **CAP Theorem** proves that a distributed data store can simultaneously guarantee at most two out of the following three properties:
- **Consistency ($C$)**: Every read receives the most recent write or an error.
- **Availability ($A$)**: Every non-failing node returns a non-error response for every request (without guarantee it is the most recent write).
- **Partition Tolerance ($P$)**: The system continues to operate despite arbitrary packet loss or network partitions.

Because network partitions ($P$) cannot be avoided in real networks, every distributed architecture is a choice between **CP (Consistency over Availability)** and **AP (Availability over Consistency)**.

In this lesson, you will master the CAP and PACELC theorems, analyze CP vs AP trade-offs in banking and social platforms, and implement concurrency conflict detection using JPA Optimistic Locking.

---

## 1. CAP & PACELC Trade-Off Decision Tree

``` mermaid
flowchart TD
    Start["Distributed System Network Event"]
    PartitionCheck{"Is there a Network Partition (P)?"}

    subgraph PartitionActive["During Network Partition (P)"]
        ChoiceCP["CP Choice: Prioritize Consistency"]
        ChoiceAP["AP Choice: Prioritize Availability"]
        
        CPAction["Reject writes or block reads until partition heals (Prevent double-spending)"]
        APAction["Accept writes on local node and synchronize eventually (Risk dirty reads)"]
        
        ChoiceCP --> CPAction
        ChoiceAP --> APAction
    end

    subgraph NormalState["Normal Operations (Else: E)"]
        ChoiceLat["Choose Low Latency (L)"]
        ChoiceCons["Choose Strong Consistency (C)"]
        
        LatAction["Read from local memory/replica without waiting for master sync"]
        ConsAction["Wait for all replica acknowledgments before returning OK"]
        
        ChoiceLat --> LatAction
        ChoiceCons --> ConsAction
    end

    Start --> PartitionCheck
    PartitionCheck -->|Yes: Partition Occurred| PartitionActive
    PartitionCheck -->|No: Healthy Network| NormalState
```

---

## 2. CP vs AP Real-World Systems Comparison

| Attribute | CP Architecture (Consistency Focus) | AP Architecture (Availability Focus) |
| :--- | :--- | :--- |
| **Core Philosophy** | Better to return an error than return stale or incorrect data. | Better to return stale data than return an error. |
| **Ideal Domains** | Bank ledgers, stock trading, credit card payments, seat booking. | Social media likes, shopping cart drafts, analytics, video views. |
| **Data Stores** | Relational DBs (PostgreSQL, MySQL), Spanner, etcd, Redis Sentinel. | Apache Cassandra, Amazon DynamoDB, CouchDB. |
| **Failure Response** | Returns `503 Service Unavailable` or `409 Conflict`. | Returns `200 OK` with eventual synchronization. |

---

## 3. The PACELC Theorem Extension

The **PACELC Theorem** extends CAP by explaining system behavior during normal (non-partitioned) operations:

$$\text{If } \mathbf{P} \text{ (Partition)}, \text{ choose between } \mathbf{A} \text{ and } \mathbf{C}; \quad \mathbf{E} \text{ (Else)}, \text{ choose between } \mathbf{L} \text{ (Latency) and } \mathbf{C} \text{ (Consistency)}.$$

Examples:
- **PostgreSQL / Spanner**: **PC/EC** (Consistent during partitions, Consistent during normal operations).
- **Cassandra / DynamoDB**: **PA/EL** (Available during partitions, Low Latency during normal operations).
- **MongoDB**: **PC/EC** by default (can be configured for PA/EL with read preferences).

---

## 4. Defending CP Systems: JPA Optimistic Locking (`@Version`)

In a CP payment system, two concurrent transactions must not deduct funds from the same account balance simultaneously. **Optimistic Locking** detects concurrent modifications at commit time without holding blocking database row locks:

```java
package com.example.model;

import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "bank_accounts")
@Getter
@Setter
@NoArgsConstructor
public class BankAccount {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String accountNumber;
    private double balance;

    /**
     * 🔒 Optimistic Lock Version: Incremented automatically on every SQL UPDATE.
     * If two threads attempt to update version 5 simultaneously, one succeeds (moves to v6)
     * and the other throws OptimisticLockException!
     */
    @Version
    private Long version;

    public BankAccount(String accountNumber, double balance) {
        this.accountNumber = accountNumber;
        this.balance = balance;
    }
}
```

### Handling Concurrent Clashes with Spring Retry

```java
package com.example.service;

import com.example.model.BankAccount;
import com.example.repository.BankAccountRepository;
import jakarta.persistence.OptimisticLockException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.orm.ObjectOptimisticLockingFailureException;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Slf4j
@Service
@RequiredArgsConstructor
public class AccountTransferService {

    private final BankAccountRepository accountRepository;

    /**
     * Retries automatically if another concurrent thread committed an update first
     */
    @Retryable(
            retryFor = {OptimisticLockException.class, ObjectOptimisticLockingFailureException.class},
            maxAttempts = 3,
            backoff = @Backoff(delay = 100, multiplier = 2.0)
    )
    @Transactional
    public void debitAccount(Long accountId, double amount) {
        BankAccount account = accountRepository.findById(accountId)
                .orElseThrow(() -> new RuntimeException("Account not found"));

        if (account.getBalance() < amount) {
            throw new IllegalStateException("Insufficient funds");
        }

        account.setBalance(account.getBalance() - amount);
        accountRepository.save(account);
        log.info("Successfully debited ${} from account {}", amount, accountId);
    }
}
```

---

## 5. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Consistency Dialects** | Hibernate 6.x Optimistic/Pessimistic lock modes. | Native CRDT (Conflict-Free Replicated Data Types) support for reactive multi-master models. |
| **Distributed Consensus** | External etcd/Zookeeper clients or Redisson distributed locks. | First-class Raft consensus state machine integration. |
| **Replication Health** | Actuator DataSource liveness/readiness probes. | Dynamic database topology discovery with automatic read-replica failover. |

---

## 6. Primary Sources & Further Reading

- [Brewer's CAP Theorem — Eric Brewer (IEEE Computer)](https://www.infoq.com/articles/cap-twelve-years-later-how-the-rules-have-changed/) — 12 years later reflection.
- [Designing Data-Intensive Applications — Martin Kleppmann](https://dataintensive.net/) — Chapter 8 (Trouble with Distributed Systems) and Chapter 9 (Consistency and Consensus).
- [The PACELC Theorem — Daniel Abadi](https://cs-people.bu.edu/dan/PACELC.html).

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: Why is it impossible to build a distributed system that guarantees Consistency, Availability, and Partition Tolerance simultaneously?"
    **Answer**: Because network partitions are unavoidable in physical networks; when a partition occurs, the system must choose between returning an error (sacrificing A) or returning stale data (sacrificing C).

??? question "Question 2: What is the difference between CAP and PACELC?"
    **Answer**: CAP only describes system trade-offs during a network partition, while PACELC also describes the trade-off between Latency (L) and Consistency (C) when the network is running normally.

??? question "Question 3: How does JPA `@Version` optimistic locking prevent double-spending in financial services?"
    **Answer**: It checks that the record version in the database matches the entity version in memory before updating; if another transaction updated it first, it aborts with an exception.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0067: Distributed Idempotency with Redis SETNX**](0067-distributed-idempotency-redis-setnx.md) | [**All Lessons**](index.md) | [➡️ **0069: Dockerfile Multi-Stage Builds & Docker Compose**](0069-dockerfile-multistage-builds-docker-compose.md) |

🎉 **Lesson 0068 completed! Proceed to Lesson 0069 to master containerizing production microservices with multi-stage Docker builds and Docker Compose.**
