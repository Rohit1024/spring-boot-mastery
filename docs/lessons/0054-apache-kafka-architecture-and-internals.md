---
icon: lucide/network
---

# 0054: Apache Kafka Architecture: Topics, Partitions & Consumer Groups

Traditional message queues (like RabbitMQ or ActiveMQ) track individual message consumption in memory and delete messages once acknowledged. Under high-throughput streaming workloads (millions of events per second), this model creates CPU bottlenecks and lacks replayability.

**Apache Kafka** is a horizontally scalable, fault-tolerant, **distributed append-only commit log**. Kafka retains data on disk across configurable retention windows, allowing multiple independent consumer systems to read, process, and replay events at their own pace without impacting cluster throughput.

In this lesson, you will master the internal architecture of Kafka topics, partitions, commit logs, consumer groups, rebalance protocols, and KRaft consensus.

---

## 1. Apache Kafka Core Architecture

``` mermaid
flowchart TD
    subgraph Producers["Kafka Producers"]
        OrderService["Order Service (Key: 'CUST-101')"]
        PaymentService["Payment Service (Key: 'CUST-202')"]
    end

    subgraph KafkaCluster["Kafka Cluster (KRaft Consensus)"]
        subgraph TopicOrders["Topic: 'order-events' (3 Partitions, Replication Factor 3)"]
            
            subgraph Partition0["Partition 0 (Leader: Broker 1)"]
                P0Seg["Commit Log: [Offset 0][Offset 1][Offset 2]...[HW]...[LEO]"]
            end
            
            subgraph Partition1["Partition 1 (Leader: Broker 2)"]
                P1Seg["Commit Log: [Offset 0][Offset 1][Offset 2]...[HW]...[LEO]"]
            end
            
            subgraph Partition2["Partition 2 (Leader: Broker 3)"]
                P2Seg["Commit Log: [Offset 0][Offset 1][Offset 2]...[HW]...[LEO]"]
            end
            
        end
    end

    subgraph ConsumerGroupA["Consumer Group: 'billing-service'"]
        ConsA1["Consumer 1 (Reads P0)"]
        ConsA2["Consumer 2 (Reads P1)"]
        ConsA3["Consumer 3 (Reads P2)"]
    end

    subgraph ConsumerGroupB["Consumer Group: 'analytics-pipeline'"]
        ConsB1["Consumer 1 (Reads P0, P1, P2)"]
    end

    OrderService -->|Key Hash routes to P0| Partition0
    PaymentService -->|Key Hash routes to P1| Partition1

    Partition0 --> ConsA1
    Partition1 --> ConsA2
    Partition2 --> ConsA3

    Partition0 --> ConsB1
    Partition1 --> ConsB1
    Partition2 --> ConsB1
```

---

## 2. Topics, Partitions & Disk Storage Mechanics

### Partitions as the Unit of Scalability
- A **Topic** is a logical category of messages.
- A topic is split into one or more **Partitions**. Partitions are distributed across physical Kafka brokers.
- **Strict Ordering Guarantee**: Kafka guarantees total message ordering **only within a single partition**, never across multiple partitions of the same topic.
- **Key Hashing**: When a message has a key, Kafka routes it via `murmur2(key) % num_partitions`. All events sharing the same key (e.g., `userId = 101`) always land in the same partition in sequential order.

### Physical Disk Layout (Segment Files)
Kafka stores partitions as a series of immutable segment files on the broker filesystem (`/data/kafka/order-events-0/`):

```text
00000000000000000000.log        <- The actual append-only message payloads
00000000000000000000.index      <- Offset-to-physical-byte-position lookup
00000000000000000000.timeindex  <- Timestamp-to-offset lookup
leader-epoch-checkpoint        <- Tracks leader failover boundaries
```

> [!TIP]
> **Why Kafka is Incredibly Fast on Disk**:
> 1. **Sequential Disk I/O**: Kafka only performs sequential append writes, achieving near-memory throughput speeds (hundreds of MB/s per disk).
> 2. **Zero-Copy Data Transfer (`sendfile`)**: When consumers read data, Kafka instructs the Linux kernel to transfer data directly from OS PageCache to the network socket without copying bytes into JVM user space.

---

## 3. Consumer Groups & Partition Assignment

A **Consumer Group** is a collection of consumer instances collaborating to consume a topic:

| Scenario | Behavior | Performance Impact |
| :--- | :--- | :--- |
| **Consumers == Partitions** (3 consumers, 3 partitions) | Ideal 1:1 mapping. Each consumer processes 1 partition. | Maximum parallelism with balanced load. |
| **Consumers < Partitions** (2 consumers, 4 partitions) | Active consumers assigned multiple partitions (e.g. Cons 1 has P0+P1, Cons 2 has P2+P3). | Full consumption, higher load per consumer. |
| **Consumers > Partitions** (5 consumers, 3 partitions) | Surplus consumers (2 instances) remain **idle** as hot standbys. | Waste of compute; cannot exceed partition count. |

### Consumer Rebalancing Protocols

``` mermaid
flowchart TD
    subgraph EagerRebalance["Eager Rebalance (Legacy)"]
        E1["1. Revoke ALL Partitions from ALL Consumers"]
        E2["2. Entire Consumer Group Stops Processing (Stop-The-World)"]
        E3["3. Rejoin Group & Reassign Partitions from Scratch"]
        E1 --> E2 --> E3
    end

    subgraph CooperativeRebalance["Cooperative Sticky Rebalance (Modern Default)"]
        C1["1. Determine only partitions that need migration"]
        C2["2. Unaffected consumers keep processing without interruption"]
        C3["3. Seamless incremental assignment"]
        C1 --> C2 --> C3
    end
```

---

## 4. Offsets, High Watermark & Replication

- **LEO (Log End Offset)**: The offset of the next record to be written to a partition leader.
- **HW (High Watermark)**: The offset of the latest record replicated across all **In-Sync Replicas (ISR)**. Consumers can only read messages up to the High Watermark to prevent dirty reads.
- **`__consumer_offsets`**: An internal, compacted Kafka topic where consumer group commit states are durably tracked.

```text
Partition 0 Commit Log:
[Offset 0] [Offset 1] [Offset 2] [Offset 3] [Offset 4] [Offset 5]
                                      ▲                      ▲
                                      │                      │
                             High Watermark (HW)       Log End Offset (LEO)
                           (Replicated to all ISR)    (Written to Leader only)
                         <-- Visible to Consumers --> <-- In-Flight Replication -->
```

---

## 5. KRaft (Kafka Raft) vs ZooKeeper

Prior to Kafka 3.x, Kafka relied on external Apache ZooKeeper clusters to manage broker metadata, leader elections, and topic schemas.

Starting with Kafka 3.3+ and mandated in Kafka 4.0+, **KRaft (Kafka Raft Metadata mode)** embeds consensus directly within Kafka controllers:
- Eliminates external ZooKeeper dependencies.
- Scales to millions of partitions per cluster with near-instant controller failover.
- Simplifies operational deployments (single binary and unified Docker containers).

---

## 6. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Kafka Client Library** | Apache Kafka Client 3.x with KRaft metadata mode. | Kafka Client 4.x (Zero ZooKeeper support, native KRaft only). |
| **Partition Assignment** | `CooperativeStickyAssignor` configured as standard partition strategy. | Next-gen KIP-848 Server-Side Consumer Group Rebalance protocol. |
| **GraalVM Native Support** | Requires manual reflection and JNI reachability metadata for native binaries. | Out-of-the-box AOT compiled Kafka consumers and producers. |

---

## 7. Primary Sources & Further Reading

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/) — Core architecture, storage internals, and protocol specification.
- [Kafka: The Definitive Guide (O'Reilly)](https://www.oreilly.com/library/view/kafka-the-definitive/9781492043072/) — Authoritative text on partitions, ISR, and consumer groups.
- [KIP-848: The Next Generation Consumer Rebalance Protocol](https://cwiki.apache.org/confluence/display/KAFKA/KIP-848%3A+The+Next+Generation+Consumer+Rebalance+Protocol).

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: Why does Kafka guarantee message ordering only within a single partition rather than across the whole topic?"
    **Answer**: To enable horizontal scaling; maintaining a single global sequence across distributed brokers would introduce centralized lock contention and eliminate parallel throughput.

??? question "Question 2: If a topic has 4 partitions and a consumer group has 6 active consumers, how many consumers will actively process messages?"
    **Answer**: Only 4 consumers will actively process messages (1 partition per consumer), while the remaining 2 consumers will remain idle as standby replicas.

??? question "Question 3: What is the significance of the High Watermark (HW) in Kafka replication?"
    **Answer**: It represents the highest offset replicated to all In-Sync Replicas (ISR); consumers can only read up to the High Watermark to prevent reading uncommitted data.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0053: Redis Pub/Sub Messaging for Real-Time Event Fanout**](0053-redis-pub-sub-messaging.md) | [**All Lessons**](index.md) | [➡️ **0055: Kafka Producer & Consumer with Spring Kafka & DLQ**](0055-kafka-producer-consumer-spring-dlq.md) |

🎉 **Lesson 0054 completed! Proceed to Lesson 0055 to build resilient Spring Boot Kafka producers, consumers, error handlers, and Dead Letter Queues.**
