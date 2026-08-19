---
icon: lucide/bug
---

# Troubleshooting Spring Batch and scheduler locking pitfalls

Batch pipelines and scheduled tasks run asynchronously, often without real-time supervision. Failures in batch chunk commits, state checkpointing, or multi-instance scheduler synchronization can corrupt data or stall processing cycles.

Here are diagnostic workflows and resolutions for Spring Batch and distributed scheduler failures.

---

## 1. Diagnostic decision tree

``` mermaid
flowchart TD
    Start["Batch / Scheduling Failure Detected"] --> ErrType{"Identify Failure Mode"}

    ErrType -->|JobInstanceAlreadyCompleteException| ParamErr["1. Identical Identifying Parameters"]
    ErrType -->|SkipLimitExceededException / Job Failed| SkipErr["2. Unhandled Exception or Limit Breach"]
    ErrType -->|Duplicate Records in Multi-Threaded Step| ThreadErr["3. Stateful Reader Race Condition"]
    ErrType -->|All K8s Pods Execute Scheduled Task| LockErr["4. Missing / Misconfigured ShedLock"]

    ParamErr --> FixParam["Add unique run timestamp / non-identifying parameter"]
    SkipErr --> FixSkip["Add .skip(Exception.class) and increase .skipLimit()"]
    ThreadErr --> FixThread["Wrap in SynchronizedItemStreamReader & setSaveState(false)"]
    LockErr --> FixLock["Verify shedlock table schema & @SchedulerLock annotation"]
```

---

## 2. Issue 1: `JobInstanceAlreadyCompleteException`

### Symptoms
```text
org.springframework.batch.core.repository.JobInstanceAlreadyCompleteException: 
A job instance already exists and is complete for parameters={billingMonth=2026-08}. 
If you want to run this job again, use a different set of parameters.
```

### Root cause
Spring Batch enforces idempotency; a `JobInstance` identified by a specific set of identifying parameters cannot run again once its status reaches `COMPLETED` in `BATCH_JOB_EXECUTION`.

### Resolution
Add a non-identifying timestamp parameter (`identifying = false`) to each run, or use `RunIdIncrementer`:

```java
JobParameters params = new JobParametersBuilder()
        // Identifying parameter: defines the business cycle
        .addString("billingMonth", "2026-08", true)
        // Non-identifying parameter: unique run timestamp that permits new executions
        .addLong("timestamp", System.currentTimeMillis(), false)
        .toJobParameters();

jobLauncher.run(billingJob, params);
```

---

## 3. Issue 2: Race conditions and duplicates in multithreaded steps

### Symptoms
In a multithreaded chunk step, duplicate records appear in the database, some CSV lines are randomly skipped, or the reader throws `ConcurrentModificationException` or `NullPointerException`.

### Root cause
`FlatFileItemReader` and `JdbcCursorItemReader` are not thread-safe; their internal line counters and cursor positions mutate concurrently when multiple threads call `.read()`.

### Diagnostic flowchart

``` mermaid
sequenceDiagram
    autonumber
    actor T1 as Worker Thread 1
    actor T2 as Worker Thread 2
    participant Reader as FlatFileItemReader (Unsynchronized)

    T1->>Reader: read() (Reads line 42, updates lineCount to 43)
    T2->>Reader: read() [Concurrent Race]
    Note over Reader: Cursor collision. Line 43 is skipped or read twice.
    Reader-->>T1: Returns Record 42
    Reader-->>T2: Returns Record 42 (Duplicate Data)
```

### Resolution
Wrap the reader in `SynchronizedItemStreamReader` and set `.setSaveState(false)`:

```java
@Bean
public SynchronizedItemStreamReader<CustomerDto> synchronizedReader(FlatFileItemReader<CustomerDto> reader) {
    reader.setSaveState(false);
    return new SynchronizedItemStreamReaderBuilder<CustomerDto>()
            .delegate(reader)
            .build();
}
```

---

## 4. Issue 3: Concurrent execution of `@Scheduled` tasks in Kubernetes

### Symptoms
Multiple Kubernetes pods execute the same `@Scheduled` cron job at the exact same second, causing duplicate notifications, double charging, or deadlock collisions in the database.

### Root cause
Spring's `@Scheduled` annotation is strictly in-memory within a single JVM. Without a distributed lock coordinator, every replica pod executes the task simultaneously.

### Resolution
1. Verify the `shedlock` table exists in PostgreSQL / MySQL:
   ```sql
   CREATE TABLE shedlock (
       name VARCHAR(64) NOT NULL PRIMARY KEY,
       lock_until TIMESTAMP NOT NULL,
       locked_at TIMESTAMP NOT NULL,
       locked_by VARCHAR(255) NOT NULL
   );
   ```
2. Annotate the scheduled method with `@SchedulerLock`:
   ```java
   @Scheduled(cron = "0 0 2 * * ?")
   @SchedulerLock(
       name = "nightlyBillingLock",
       lockAtMostFor = "10m",
       lockAtLeastFor = "30s" // Protects against clock drift and sub-second execution
   )
   public void processNightlyBilling() {
       // Only one pod executes this.
   }
   ```

---

## Navigation and debugging index

| Previous | Debugging index | Next |
| :--- | :---: | ---: |
| [**Troubleshooting Jib and GraalVM pitfalls**](jib-cloud-auth-and-graalvm-native-pitfalls.md) | [**All debugging guides**](index.md) | [**GraphQL, gRPC, and WebSocket troubleshooting**](graphql-n-plus-1-grpc-and-websocket-broker-pitfalls.md) |
