---
icon: lucide/shield-alert
---

# 0035: Fault tolerance in Spring Batch: Skip, retry, and rollback policies

In large-scale production batch jobs processing millions of records, errors are inevitable. A corrupted CSV row, an invalid email format, a transient database deadlock, or a temporary third-party API timeout will occur.

Failing an entire 6-hour batch job because of **1 malformed record out of 2,000,000** wastes compute, violates business SLAs, and requires urgent developer intervention.

In this lesson, you will master Spring Batch's **Fault Tolerance subsystem**: configuring intelligent **Skip Policies**, implementing **Retry Policies with Exponential Backoff**, auditing skipped records via **Listeners**, and managing transactional rollbacks.

---

## 1. Fault tolerance decision model: Abort vs skip vs retry

``` mermaid
flowchart TD
    ExceptionThrown["Exception Thrown during Read / Process / Write"] --> CheckType{"What is the Exception Nature?"}

    CheckType -->|Transient or Recoverable Failure| RetryFlow["1. Evaluate Retry Policy<br/><i>(DB Deadlock, REST 503, Network Timeout)</i>"]
    CheckType -->|Malformed Data or Bad Record| SkipFlow["2. Evaluate Skip Policy<br/><i>(NumberFormatException, ValidationFailure)</i>"]
    CheckType -->|Fatal System Failure| AbortJob["3. Fatal Abort<br/><i>(Disk Full, DB Down, Auth Error)</i>"]

    RetryFlow --> RetryLimit{"Retry count < limit?"}
    RetryLimit -->|Yes| BackOff["Wait BackOff Duration & Retry Item"]
    RetryLimit -->|No| FallbackToSkip["Max Retries Exceeded -> Evaluate Skip"]

    SkipFlow --> SkipLimit{"Skip count < limit?"}
    SkipLimit -->|Yes| LogDeadLetter["Trigger SkipListener & Continue Next Item ✅"]
    SkipLimit -->|No| ExceedSkip["SkipLimitExceededException (Job Marked FAILED) ❌"]
```

---

## 2. Configuring skip policies (`skip` `skipLimit`)

A Skip Policy allows Spring Batch to discard bad records and continue processing the remaining chunk without rolling back the entire job:

```java
package com.example.batch.config;

import com.example.batch.dto.CustomerCsvRecord;
import com.example.batch.entity.CustomerEntity;
import com.example.batch.exception.InvalidCustomerRecordException;
import com.example.batch.listener.CustomerSkipListener;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.batch.item.ItemReader;
import org.springframework.batch.item.ItemWriter;
import org.springframework.batch.item.file.transform.FlatFileParseException;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.PlatformTransactionManager;

@Configuration
public class FaultTolerantBatchConfig {

    @Bean
    public Step robustIngestionStep(
            JobRepository jobRepository,
            PlatformTransactionManager transactionManager,
            ItemReader<CustomerCsvRecord> reader,
            ItemProcessor<CustomerCsvRecord, CustomerEntity> processor,
            ItemWriter<CustomerEntity> writer,
            CustomerSkipListener skipListener) {

        return new StepBuilder("robustIngestionStep", jobRepository)
                .<CustomerCsvRecord, CustomerEntity>chunk(100, transactionManager)
                .reader(reader)
                .processor(processor)
                .writer(writer)
                
                // 1. Enable Fault Tolerance
                .faultTolerant()
                
                // 2. Configure Skippable Exceptions
                .skip(FlatFileParseException.class)
                .skip(InvalidCustomerRecordException.class)
                .skip(NumberFormatException.class)
                // Threshold: If more than 50 bad records occur, abort the job
                .skipLimit(50)
                
                // 3. Register Audit Listener for Skipped Records
                .listener(skipListener)
                .build();
    }
}
```

---

## 3. Configuring retry with exponential backoff

For transient database deadlocks or network hiccups, retrying the operation with backoff prevents unnecessary job termination:

```java
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.dao.DeadlockLoserDataAccessException;
import org.springframework.dao.TransientDataAccessException;
import org.springframework.web.client.ResourceAccessException;

// Inside Step configuration:
.faultTolerant()
// Retry on database lock contention or network drop
.retry(DeadlockLoserDataAccessException.class)
.retry(TransientDataAccessException.class)
.retry(ResourceAccessException.class)
.retryLimit(3) // Retry up to 3 times before failing or skipping
```

---

## 4. Auditing skipped records: `SkipListener`

Never discard bad records silently! A `SkipListener` logs discarded items to an audit dead-letter database table or Kafka topic for remediation:

```java
package com.example.batch.listener;

import com.example.batch.dto.CustomerCsvRecord;
import com.example.batch.entity.CustomerEntity;
import com.example.batch.repository.DeadLetterAuditRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.core.SkipListener;
import org.springframework.batch.item.file.FlatFileParseException;
import org.springframework.stereotype.Component;

@Component
public class CustomerSkipListener implements SkipListener<CustomerCsvRecord, CustomerEntity> {

    private static final Logger log = LoggerFactory.getLogger(CustomerSkipListener.class);
    private final DeadLetterAuditRepository auditRepository;

    public CustomerSkipListener(DeadLetterAuditRepository auditRepository) {
        this.auditRepository = auditRepository;
    }

    @Override
    public void onSkipInRead(Throwable t) {
        if (t instanceof FlatFileParseException ffpe) {
            log.error("Corrupted CSV row skipped at line {}: raw input='{}'", 
                      ffpe.getLineNumber(), ffpe.getInput());
            auditRepository.saveDeadLetterLog("CSV_READ", ffpe.getInput(), t.getMessage());
        }
    }

    @Override
    public void onSkipInProcess(CustomerCsvRecord item, Throwable t) {
        log.warn("Record skipped during processing: item={}, reason={}", item, t.getMessage());
        auditRepository.saveDeadLetterLog("PROCESS_VALIDATION", item.toString(), t.getMessage());
    }

    @Override
    public void onSkipInWrite(CustomerEntity item, Throwable t) {
        log.error("Database write failure for item: {}, error={}", item, t.getMessage());
        auditRepository.saveDeadLetterLog("DB_WRITE_ERROR", item.toString(), t.getMessage());
    }
}
```

---

## 5. Rollback control: `noRollback`

By default, any unhandled exception in a chunk triggers a transaction rollback. If certain business exceptions should NOT invalidate already processed items in the current transaction, mark them with `noRollback`:

```java
.faultTolerant()
.noRollback(NonCriticalNotificationException.class)
```

---

## 6. Spring Boot 3 vs Spring Boot 4: Fault tolerance evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Batch 5)"]
        SkipRetry5["Class-Based .skip() and .retry() Step Declarations"]
        ManualDLQ["Manual DeadLetterAudit JDBC Logging"]
        PlatformBackoff["Thread.sleep() based ExponentialBackoff"]
    end

    subgraph SB4["Spring Boot 4.x (Batch 6)"]
        TypeSafePolicies["Type-Safe Sealed Exception Policies"]
        NativeKafkaDLQ["Out-of-the-Box Kafka Dead-Letter-Queue Step Writers"]
        VirtualThreadYield["Non-Blocking Loom BackOff Yielding"]
    end

    SB3 ==>|Resilience & Virtual Threading| SB4
```

### Key differences and configuration comparison

| Fault Tolerance Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Retry Backoff Mechanism** | Standard `Thread.sleep()` blocking underlying OS platform thread. | **Virtual Thread Non-Blocking Yielding**: Millions of concurrent step retries yield carrier threads without resource starvation. |
| **Dead-Letter Infrastructure** | Required custom `SkipListener` and audit database table integration. | **Auto-Configured Dead-Letter Streaming**: Direct declarative emission of skipped items to Kafka DLQs or S3 buckets. |
| **Skip Limit Tracking** | Relied solely on total count in `BATCH_STEP_EXECUTION.READ_SKIP_COUNT`. | **Dimensional Metrics & Alerts**: Emits Micrometer / OpenTelemetry tags per specific exception class. |

---

## 7. Primary sources and further reading

- [Spring Batch Fault Tolerance Documentation](https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing.html#faultTolerance), Official guide to skip, retry, and rollback configuration.
- [Spring Retry Official Repository](https://github.com/spring-projects/spring-retry), Backoff policies and retry templates.
- [Baeldung: Spring Batch Skip and Retry](https://www.baeldung.com/spring-batch-skip-retry), Hands-on examples of resilient batch steps.

---

## 8. Knowledge check and practice

??? question "Question 1: What happens if the number of skipped records exceeds the configured `skipLimit(50)`?"
    **Answer**: Spring Batch terminates the step by throwing `SkipLimitExceededException` and marks the `JobExecution` status as `FAILED` in the `BATCH_JOB_EXECUTION` database table.

??? question "Question 2: In which phase of chunk processing can a `SkipListener` intercept errors?"
    **Answer**: In all three phases: `onSkipInRead` (parsing failures), `onSkipInProcess` (validation failures), and `onSkipInWrite` (database constraint or persistence errors).

??? question "Question 3: Why should transient database deadlocks (`DeadlockLoserDataAccessException`) be configured for retry rather than skip?"
    **Answer**: Deadlocks are temporary concurrency collisions; retrying after a brief backoff almost always succeeds, preserving transaction integrity without discarding valid business records.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0034: Chunk-Oriented Processing**](0034-chunk-oriented-processing-readers-writers.md) | [**All Lessons**](index.md) | [ **0036: Multi-Threaded Steps & Partitioning**](0036-multithreaded-steps-and-partitioning.md) |
