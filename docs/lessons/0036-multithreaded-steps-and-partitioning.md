---
icon: lucide/cpu
---

# 0036: High-scale batch processing: Multithreaded steps and partitioning

When a batch job must process tens of millions of records within a strict 30-minute maintenance window, executing steps on a single thread will inevitably breach production SLAs.

Spring Batch provides four robust scaling architectures to parallelize execution across multi-core CPUs and distributed compute clusters: **Multi-Threaded Steps**, **Parallel Steps (Split Flows)**, **Local Partitioning**, and **Remote Partitioning**.

In this lesson, you will master thread-safety caveats with batch readers, configure high-performance Multi-Threaded Steps with Virtual Threads, implement Master-Worker Step Partitioning, and scale throughput by orders of magnitude.

---

## 1. Batch scaling architectures compared

``` mermaid
flowchart TD
    subgraph MultiThreaded["1. Multi-Threaded Step (Single Process)"]
        ReaderShared["Shared Thread-Safe ItemReader"]
        Pool["Thread Pool / Virtual Threads"]
        ChunkA["Thread 1: Process & Write Chunk A"]
        ChunkB["Thread 2: Process & Write Chunk B"]
        ChunkC["Thread 3: Process & Write Chunk C"]
        
        ReaderShared --> Pool --> ChunkA & ChunkB & ChunkC
    end

    subgraph Partitioned["2. Step Partitioning (Master-Worker Architecture)"]
        Master["Master Step (Partitioner)"]
        Worker1["Worker Step 1: Range 1 - 100,000"]
        Worker2["Worker Step 2: Range 100,001 - 200,000"]
        Worker3["Worker Step 3: Range 200,001 - 300,000"]
        
        Master -->|Spawns Independent Steps| Worker1 & Worker2 & Worker3
    end

    MultiThreaded ~~~ Partitioned
```

### Architectural comparison

| Strategy | Thread-Safety Complexity | Restartability State | Best Use Case |
| :--- | :--- | :--- | :--- |
| **Multi-Threaded Step** | **High** (Reader must be synchronized or thread-safe). | ❌ Non-deterministic (No checkpoint restart). | Simple in-memory I/O scaling on multi-core servers. |
| **Parallel Step (Flow)** | **None** (Steps are completely isolated). | ✅ Fully restartable. | Independent workflows (e.g. Ingesting Users AND Ingesting Products simultaneously). |
| **Local Partitioning** | **Low** (Each worker step has its own isolated reader). | ✅ **100% Restartable per partition**. | **Large database table ranges & multi-file processing**. |
| **Remote Partitioning** | **Low** (Workers run on separate Kubernetes Pods via Kafka/JMS). | ✅ 100% Restartable. | Ultra-scale enterprise datasets (100M+ records). |

---

## 2. Multi-threaded step implementation thread-safety

### The thread-safety trap
Standard `ItemReader` implementations (like `FlatFileItemReader` or `JdbcCursorItemReader`) maintain internal state (such as file cursor line numbers). If multiple threads call `.read()` concurrently without synchronization, race conditions will duplicate, skip, or corrupt records!

### Solutions for multi-threaded steps
1. Wrap stateful readers with `SynchronizedItemStreamReader`.
2. Use inherently thread-safe paging readers (`JdbcPagingItemReader` or `JpaPagingItemReader`).
3. Set `.saveState(false)` on the reader because execution order across threads is non-deterministic.

### Multi-threaded step configuration
```java
package com.example.batch.config;

import com.example.batch.dto.CustomerCsvRecord;
import com.example.batch.entity.CustomerEntity;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.batch.item.ItemWriter;
import org.springframework.batch.item.file.FlatFileItemReader;
import org.springframework.batch.item.support.SynchronizedItemStreamReader;
import org.springframework.batch.item.support.builder.SynchronizedItemStreamReaderBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.SimpleAsyncTaskExecutor;
import org.springframework.core.task.TaskExecutor;
import org.springframework.transaction.PlatformTransactionManager;

@Configuration
public class MultiThreadedBatchConfig {

    @Bean
    public SynchronizedItemStreamReader<CustomerCsvRecord> synchronizedReader(FlatFileItemReader<CustomerCsvRecord> rawReader) {
        // Disables state saving for multi-threaded safety
        rawReader.setSaveState(false);
        return new SynchronizedItemStreamReaderBuilder<CustomerCsvRecord>()
                .delegate(rawReader)
                .build();
    }

    @Bean
    public TaskExecutor batchVirtualThreadExecutor() {
        SimpleAsyncTaskExecutor executor = new SimpleAsyncTaskExecutor("batch-vt-");
        executor.setVirtualThreads(true); // Uses Java 21 virtual threads
        return executor;
    }

    @Bean
    public Step multiThreadedStep(
            JobRepository jobRepository,
            PlatformTransactionManager transactionManager,
            SynchronizedItemStreamReader<CustomerCsvRecord> synchronizedReader,
            ItemProcessor<CustomerCsvRecord, CustomerEntity> processor,
            ItemWriter<CustomerEntity> writer,
            TaskExecutor batchVirtualThreadExecutor) {

        return new StepBuilder("multiThreadedStep", jobRepository)
                .<CustomerCsvRecord, CustomerEntity>chunk(500, transactionManager)
                .reader(synchronizedReader)
                .processor(processor)
                .writer(writer)
                // Parallelize chunk processing across virtual threads
                .taskExecutor(batchVirtualThreadExecutor)
                .build();
    }
}
```

---

## 3. Step partitioning (master-worker architecture)

Partitioning divides a large dataset into discrete slices (e.g. by database ID ranges or file names). A **Master Step** delegates each slice to a **Worker Step** running on a dedicated thread with its own independent reader, processor, and writer:

``` mermaid
flowchart TD
    Master["Master Step (ColumnRangePartitioner)"] -->|Grid Size = 4| P1 & P2 & P3 & P4
    
    P1["Partition 0: IDs 1 to 250,000"] --> W1["Worker Step 0 (Thread 1)"]
    P2["Partition 1: IDs 250,001 to 500,000"] --> W2["Worker Step 1 (Thread 2)"]
    P3["Partition 2: IDs 500,001 to 750,000"] --> W3["Worker Step 2 (Thread 3)"]
    P4["Partition 3: IDs 750,001 to 1,000,000"] --> W4["Worker Step 3 (Thread 4)"]
    
    W1 --> Checkpoint1["BATCH_STEP_EXECUTION (Worker 0: COMPLETED)"]
    W2 --> Checkpoint2["BATCH_STEP_EXECUTION (Worker 1: COMPLETED)"]
    W3 --> Checkpoint3["BATCH_STEP_EXECUTION (Worker 2: COMPLETED)"]
    W4 --> Checkpoint4["BATCH_STEP_EXECUTION (Worker 3: COMPLETED)"]
```

### Implementing a custom `ColumnRangePartitioner`
```java
package com.example.batch.partitioner;

import org.springframework.batch.core.partition.support.Partitioner;
import org.springframework.batch.item.ExecutionContext;

import java.util.HashMap;
import java.util.Map;

public class ColumnRangePartitioner implements Partitioner {

    private final long minId;
    private final long maxId;

    public ColumnRangePartitioner(long minId, long maxId) {
        this.minId = minId;
        this.maxId = maxId;
    }

    @Override
    public Map<String, ExecutionContext> partition(int gridSize) {
        Map<String, ExecutionContext> result = new HashMap<>();
        long targetSize = (maxId - minId) / gridSize + 1;

        long start = minId;
        long end = start + targetSize - 1;

        for (int i = 0; i < gridSize; i++) {
            ExecutionContext context = new ExecutionContext();
            context.putLong("minValue", start);
            context.putLong("maxValue", Math.min(end, maxId));
            result.put("partition" + i, context);

            start += targetSize;
            end += targetSize;
        }
        return result;
    }
}
```

---

## 4. Spring Boot 3 vs Spring Boot 4: High-scale batch evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Batch 5)"]
        PlatformPools["ThreadPoolTaskExecutor (Platform Threads)"]
        JmsKafkaRemote["Spring Batch Integration (Spring Integration JMS/Kafka)"]
        ManualSyncReader["Manual SynchronizedItemStreamReader Wrapping"]
    end

    subgraph SB4["Spring Boot 4.x (Batch 6)"]
        VirtualThreadStep["Virtual-Thread Native SimpleAsyncTaskExecutor Standard"]
        DistributedBatchStarters["Cloud Native Distributed Chunk Starters"]
        ThreadSafePaging["Auto-ThreadSafe Keyset Paging Readers"]
    end

    SB3 ==>|Massive Concurrency & Cloud-Native Scaling| SB4
```

### Key differences and configuration comparison

| Scaling Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Step Threading Engine** | Bound by OS thread pool limits (`corePoolSize=10`, `maxPoolSize=50`). | **Virtual Thread Native**: Thousands of concurrent worker chunks with zero thread starvation. |
| **Restartability in Partitioning** | Checkpointed individually in `BATCH_STEP_EXECUTION` for each worker slice. | **Structured Concurrency Checkpointing**: Master step aggregates failures and auto-retries failed partitions. |
| **Distributed Orchestration** | Required custom Spring Integration channels and message brokers. | **Kubernetes Job Orchestrator Native**: Direct integration with K8s indexed job completions. |

---

## 5. Primary sources and further reading

- [Spring Batch Scaling and Parallel Processing Guide](https://docs.spring.io/spring-batch/reference/scalability.html), Official documentation on Multi-Threaded Steps and Partitioning.
- [Project Loom & Spring Batch Virtual Thread Optimization](https://spring.io/blog), High-throughput batch processing with virtual threads.
- [Spring Batch Remote Chunking with Apache Kafka](https://github.com/spring-projects/spring-batch/tree/main/spring-batch-integration), Multi-node worker integration patterns.

---

## 6. Knowledge check and practice

??? question "Question 1: Why must stateful readers like `FlatFileItemReader` have `.setSaveState(false)` or be wrapped in `SynchronizedItemStreamReader` when used in Multi-Threaded Steps?"
    **Answer**: Because multiple worker threads concurrently call `.read()`; without synchronization, race conditions corrupt cursor positions, and stateful checkpoint offsets cannot be saved deterministically.

??? question "Question 2: What is the primary advantage of Step Partitioning over Multi-Threaded Steps?"
    **Answer**: Partitioning isolates data slices into independent worker steps, ensuring complete thread-safety and full restartability per partition in the `JobRepository`.

??? question "Question 3: How does Java 21 Virtual Threading transform Spring Batch Multi-Threaded step performance?"
    **Answer**: It eliminates OS thread pool capacity bottlenecks, allowing thousands of I/O-heavy database or REST chunks to process concurrently with near-zero memory overhead.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0035: Fault Tolerance (Skip & Retry)**](0035-fault-tolerance-skip-retry-policies.md) | [**All Lessons**](index.md) | [ **0037: Quartz Scheduling & ShedLock**](0037-quartz-scheduler-and-shedlock-distributed-locking.md) |
