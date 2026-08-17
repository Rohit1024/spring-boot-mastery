---
icon: lucide/calendar-range
---

# Spring Batch, Quartz & ShedLock Cheatsheet

A rapid reference guide for Spring Batch 5 domain models, Chunk-Oriented Processing, Fault Tolerance (Skip & Retry), ShedLock distributed locks, and Clustered Quartz configuration.

---

## 1. Spring Batch 5 Configuration Snippets

### Standard Chunk Step with Skip & Retry:
```java
@Bean
public Step processChunkStep(
        JobRepository jobRepository,
        PlatformTransactionManager transactionManager,
        ItemReader<InputDto> reader,
        ItemProcessor<InputDto, OutputEntity> processor,
        ItemWriter<OutputEntity> writer,
        SkipListener<InputDto, OutputEntity> skipListener) {

    return new StepBuilder("processChunkStep", jobRepository)
            .<InputDto, OutputEntity>chunk(250, transactionManager)
            .reader(reader)
            .processor(processor)
            .writer(writer)
            .faultTolerant()
            .skip(FlatFileParseException.class)
            .skip(ValidationException.class)
            .skipLimit(50)
            .retry(DeadlockLoserDataAccessException.class)
            .retryLimit(3)
            .listener(skipListener)
            .build();
}
```

### Multi-Threaded Step with Virtual Threads:
```java
@Bean
public Step multiThreadedStep(
        JobRepository jobRepository,
        PlatformTransactionManager txManager,
        SynchronizedItemStreamReader<InputDto> synchronizedReader,
        ItemProcessor<InputDto, OutputEntity> processor,
        ItemWriter<OutputEntity> writer) {

    SimpleAsyncTaskExecutor executor = new SimpleAsyncTaskExecutor("batch-vt-");
    executor.setVirtualThreads(true);

    return new StepBuilder("multiThreadedStep", jobRepository)
            .<InputDto, OutputEntity>chunk(500, txManager)
            .reader(synchronizedReader)
            .processor(processor)
            .writer(writer)
            .taskExecutor(executor)
            .build();
}
```

---

## 2. Spring Batch Schema Tables Reference

| Table Name | Primary Role |
| :--- | :--- |
| **`BATCH_JOB_INSTANCE`** | Highest-level logical job run (stores `JOB_NAME` and `JOB_KEY`). |
| **`BATCH_JOB_EXECUTION`** | Physical execution attempt (stores `START_TIME`, `STATUS`, `EXIT_CODE`). |
| **`BATCH_JOB_EXECUTION_PARAMS`** | Parameters passed to the job execution (`STRING`, `DATE`, `LONG`). |
| **`BATCH_STEP_EXECUTION`** | Progress per step (stores `READ_COUNT`, `WRITE_COUNT`, `COMMIT_COUNT`, `SKIP_COUNT`). |
| **`BATCH_STEP_EXECUTION_CONTEXT`** | Checkpoint data for restarting failed steps. |

---

## 3. ShedLock Distributed Locking Quick Reference

### 1. PostgreSQL Schema:
```sql
CREATE TABLE shedlock (
    name VARCHAR(64) NOT NULL PRIMARY KEY,
    lock_until TIMESTAMP NOT NULL,
    locked_at TIMESTAMP NOT NULL,
    locked_by VARCHAR(255) NOT NULL
);
```

### 2. Lock Configuration & Usage:
```java
@Configuration
@EnableScheduling
@EnableSchedulerLock(defaultLockAtMostFor = "10m")
public class ShedLockConfig {
    @Bean
    public LockProvider lockProvider(DataSource dataSource) {
        return new JdbcTemplateLockProvider(
            JdbcTemplateLockProvider.Configuration.builder()
                .withJdbcTemplate(new JdbcTemplate(dataSource))
                .usingDbTime()
                .build()
        );
    }
}

// In your scheduled component:
@Scheduled(cron = "0 0 2 * * ?")
@SchedulerLock(name = "dailyBilling", lockAtMostFor = "15m", lockAtLeastFor = "30s")
public void runDailyBilling() {
    // Guaranteed to execute on AT MOST 1 server instance across your cluster!
}
```

---

## 4. Quartz Clustered Scheduling Configuration (`application.yml`)

```yaml
spring:
  quartz:
    job-store-type: jdbc
    jdbc:
      initialize-schema: always # or 'never'
    properties:
      org.quartz.scheduler.instanceName: ClusteredQuartzScheduler
      org.quartz.scheduler.instanceId: AUTO
      org.quartz.jobStore.isClustered: true
      org.quartz.jobStore.clusterCheckinInterval: 20000
```

---

## 🧭 Navigation & Cheatsheet Index

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Spring Boot Packaging & Jib Cheatsheet**](spring-boot-jib-docker-native.md) | [**All Cheatsheets**](index.md) | [➡️ **GraphQL, gRPC & WebSockets Cheatsheet**](graphql-grpc-websockets.md) |
