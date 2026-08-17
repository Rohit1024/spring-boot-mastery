---
icon: lucide/layers
---

# 0033: Spring Batch Core Architecture & JobRepository Persistence

In enterprise systems, business-critical workloads—such as overnight billing runs, bulk payroll disbursement, nightly inventory reconciliation, and data warehouse ETL—require processing millions of records reliably without human intervention.

**Spring Batch** is the industry-standard framework for enterprise batch processing, offering transactional execution, automated state checkpointing, restartability, and job history management.

In this lesson, you will master the Spring Batch 5 domain model, explore the relational `JobRepository` schema, construct modern Java-based jobs with `JobBuilder` and `StepBuilder`, and handle job parameter identity and restart mechanics.

---

## 1. Spring Batch Domain Architecture

Spring Batch decomposes batch workloads into a strict hierarchical domain model:

``` mermaid
flowchart TD
    subgraph ClientLayer["1. Job Launching Layer"]
        Launcher["JobLauncher<br/><i>(Triggers job execution with JobParameters)</i>"]
    end

    subgraph BatchDomain["2. Batch Domain Hierarchy"]
        Job["Job<br/><i>(Named workflow: 'billingJob')</i>"]
        
        subgraph StepPipeline["Step Pipeline"]
            Step1["Step 1: IngestDataStep"]
            Step2["Step 2: CalculateTaxesStep"]
            Step3["Step 3: ExportInvoicesStep"]
            
            Step1 --> Step2 --> Step3
        end
        
        Job --> StepPipeline
    end

    subgraph PersistenceLayer["3. Metadata & Checkpoint Store"]
        JobRepo["JobRepository<br/><i>(Persists executions, checkpoints & state deltas)</i>"]
        DB[(Batch Schema Tables<br/>BATCH_JOB_INSTANCE, BATCH_STEP_EXECUTION...)]
        
        JobRepo <--> DB
    end

    Launcher --> Job
    Job -.->|Records State & Checkpoints| JobRepo
    StepPipeline -.->|Records Step Progress| JobRepo
```

### Core Domain Concepts:

| Component | Responsibility |
| :--- | :--- |
| **`Job`** | The entire batch process definition containing a sequential or branched graph of `Step` definitions. |
| **`JobInstance`** | The logical run of a `Job`, uniquely identified by its name and **identifying** `JobParameters`. |
| **`JobExecution`** | A single physical execution attempt of a `JobInstance` (tracks start time, end time, exit code, status). |
| **`Step`** | An independent, sequential phase of a batch job (tasklet-based or chunk-based). |
| **`StepExecution`** | A physical execution attempt of a `Step` (tracks commit count, read count, write count, skip count). |
| **`ExecutionContext`** | A key-value state store persisted by the `JobRepository` to allow jobs to resume exactly where they failed. |
| **`JobRepository`** | The persistence mechanism responsible for saving execution status and checkpoints to relational tables. |

---

## 2. The `JobRepository` Relational Database Schema

Spring Batch maintains complete auditability by persisting state across six core relational tables:

``` mermaid
erDiagram
    BATCH_JOB_INSTANCE ||--o{ BATCH_JOB_EXECUTION : "has executions"
    BATCH_JOB_EXECUTION ||--o{ BATCH_JOB_EXECUTION_PARAMS : "receives parameters"
    BATCH_JOB_EXECUTION ||--o{ BATCH_JOB_EXECUTION_CONTEXT : "stores context"
    BATCH_JOB_EXECUTION ||--o{ BATCH_STEP_EXECUTION : "executes steps"
    BATCH_STEP_EXECUTION ||--o{ BATCH_STEP_EXECUTION_CONTEXT : "persists step state"

    BATCH_JOB_INSTANCE {
        bigint JOB_INSTANCE_ID PK
        varchar JOB_NAME
        varchar JOB_KEY
    }

    BATCH_JOB_EXECUTION {
        bigint JOB_EXECUTION_ID PK
        bigint JOB_INSTANCE_ID FK
        timestamp START_TIME
        timestamp END_TIME
        varchar STATUS
        varchar EXIT_CODE
    }

    BATCH_STEP_EXECUTION {
        bigint STEP_EXECUTION_ID PK
        bigint JOB_EXECUTION_ID FK
        varchar STEP_NAME
        varchar STATUS
        bigint COMMIT_COUNT
        bigint READ_COUNT
        bigint WRITE_COUNT
        bigint READ_SKIP_COUNT
    }
```

### Automatic Table Initialization (`application.yml`)
In Spring Boot 3+, Spring Batch tables can be created automatically:

```yaml
spring:
  batch:
    jdbc:
      initialize-schema: always # or 'embedded' (default for H2), 'never' for production DBA scripts
    job:
      enabled: false # Disable automatic execution on application startup
```

---

## 3. Configuring Jobs in Spring Batch 5

Spring Batch 5 (Spring Boot 3.x) removed legacy `@EnableBatchProcessing` boilerplate and deprecated factories (`JobBuilderFactory`, `StepBuilderFactory`). Configuration is now purely component-based:

### `BillingBatchConfig.java`
```java
package com.example.batch.config;

import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.repeat.RepeatStatus;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.PlatformTransactionManager;

@Configuration
public class BillingBatchConfig {

    @Bean
    public Job billingJob(JobRepository jobRepository, Step validateStep, Step processInvoicesStep) {
        return new JobBuilder("billingJob", jobRepository)
                .start(validateStep)
                .next(processInvoicesStep)
                .build();
    }

    @Bean
    public Step validateStep(JobRepository jobRepository, PlatformTransactionManager transactionManager) {
        return new StepBuilder("validateStep", jobRepository)
                .tasklet((contribution, chunkContext) -> {
                    System.out.println("Validating billing inputs and database connectivity...");
                    return RepeatStatus.FINISHED;
                }, transactionManager)
                .build();
    }

    @Bean
    public Step processInvoicesStep(JobRepository jobRepository, PlatformTransactionManager transactionManager) {
        return new StepBuilder("processInvoicesStep", jobRepository)
                .tasklet((contribution, chunkContext) -> {
                    System.out.println("Processing invoices...");
                    return RepeatStatus.FINISHED;
                }, transactionManager)
                .build();
    }
}
```

---

## 4. Job Launching & Parameter Identity (`JobParameters`)

When launching a job via `JobLauncher`, parameters determine whether Spring Batch creates a **new `JobInstance`** or attempts to **restart an existing failed `JobInstance`**:

``` mermaid
flowchart TD
    LaunchReq["JobLauncher.run(job, params)"] --> Lookup["Query BATCH_JOB_INSTANCE by JOB_NAME + Identifying Params"]
    
    Lookup --> Exists{"Does JobInstance exist?"}
    
    Exists -->|No| CreateInstance["Create new JobInstance & new JobExecution (STARTING)"]
    
    Exists -->|Yes| CheckStatus{"What was the last Execution Status?"}
    
    CheckStatus -->|COMPLETED| RejectDuplicate["❌ Cannot Restart: JobInstanceAlreadyCompleteException"]
    CheckStatus -->|FAILED / STOPPED| ResumeInstance["✅ Resume: Create new JobExecution for existing Instance"]
```

### Launching Programmatically via REST Controller:
```java
package com.example.batch.controller;

import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Date;

@RestController
public class JobTriggerController {

    private final JobLauncher jobLauncher;
    private final Job billingJob;

    public JobTriggerController(JobLauncher jobLauncher, Job billingJob) {
        this.jobLauncher = jobLauncher;
        this.billingJob = billingJob;
    }

    @PostMapping("/api/jobs/billing")
    public ResponseEntity<String> triggerBillingJob(@RequestParam String billingPeriod) throws Exception {
        JobParameters params = new JobParametersBuilder()
                // Identifying parameter: defines unique JobInstance per billing cycle
                .addString("billingPeriod", billingPeriod, true)
                // Non-identifying parameter: tracking execution run timestamp without altering identity
                .addDate("runDate", new Date(), false)
                .toJobParameters();

        jobLauncher.run(billingJob, params);
        return ResponseEntity.accepted().body("Job triggered successfully for period: " + billingPeriod);
    }
}
```

---

## 5. Spring Boot 3 vs Spring Boot 4: Batch Architecture Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Spring Batch 5)"]
        Batch5Builder["Direct JobBuilder & StepBuilder (No Factories)"]
        LegacyTypes["java.util.Date in JobParameters"]
        SyncLauncher["TaskExecutorJobLauncher (Thread-Bound)"]
    end

    subgraph SB4["Spring Boot 4.x (Spring Batch 6)"]
        RecordJobParams["Java Record JobParameters & java.time.Instant"]
        LoomJobLauncher["Virtual-Thread Native Concurrent Step Dispatch"]
        AOTBatchIndex["AOT Compiled Batch Metamodel"]
    end

    SB3 ==>|Modernization & Loom Acceleration| SB4
```

### Key Differences & Configuration Comparison

| Batch Capability | Spring Boot 3.x (Batch 5) | Spring Boot 4.x (Batch 6) |
| :--- | :--- | :--- |
| **Parameter Types** | Legacy `java.util.Date` and `java.lang.Long` in `JobParameters`. | **Java Time Native**: Full support for `java.time.Instant` and `java.time.LocalDate` in parameters. |
| **Concurrency Model** | Platform thread pool dispatching for concurrent jobs. | **Project Loom Virtual Threads**: Unbounded concurrent step launcher with near-zero memory footprint. |
| **AOT / Native Image Support** | Required manual `@RegisterReflectionForBinding` for all step tasklets. | **AOT Pre-Compiled Batch Metadata**: Automatic reachability inference for reader/writer/processor beans. |

---

## 6. Primary Sources & Further Reading

- [Spring Batch 5 Official Reference Guide](https://docs.spring.io/spring-batch/reference/index.html) — Core architecture, builder changes, and step configuration.
- [Spring Batch Database Schema Reference](https://docs.spring.io/spring-batch/reference/schema-appendix.html) — Detailed breakdown of all `BATCH_*` metadata tables.
- [Michael Minella: The Definitive Guide to Spring Batch](https://www.apress.com/gp/book/9781484237236) — Authoritative enterprise design patterns.

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the fundamental difference between a `JobInstance` and a `JobExecution` in Spring Batch?"
    **Answer**: A `JobInstance` represents the logical run of a job identified by unique parameters, while a `JobExecution` is a single physical execution attempt of that instance (which may fail and be retried).

??? question "Question 2: Why will Spring Batch throw a `JobInstanceAlreadyCompleteException` if you run a job with identical identifying parameters twice?"
    **Answer**: By design, Spring Batch enforces idempotency; a completed `JobInstance` cannot be re-executed with the same identifying parameters to prevent duplicate processing of business transactions.

??? question "Question 3: How does the `ExecutionContext` facilitate job restartability after a crash?"
    **Answer**: The `ExecutionContext` persists checkpoint states (such as the last read record offset) in the database, allowing steps to resume from the exact failure point without reprocessing earlier records.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0032: Containerizing Native Images with Jib**](0032-containerizing-graalvm-native-images-with-jib.md) | [**All Lessons**](index.md) | [➡️ **0034: Chunk-Oriented Processing**](0034-chunk-oriented-processing-readers-writers.md) |
