---
icon: lucide/calendar-range
---

# Spring Batch, Quartz, and ShedLock cheatsheet

Reference guide for Spring Batch 5 domain models, chunk-oriented processing, skip and retry policies, ShedLock distributed locks, and clustered Quartz configuration.

---

## 1. Spring Batch 5 configuration snippets

### Standard chunk step with skip and retry
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

### Multithreaded step with virtual threads
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

## 2. Spring Batch schema tables reference

| Table name | Primary role |
| :--- | :--- |
| `BATCH_JOB_INSTANCE` | Highest-level logical job run (stores `JOB_NAME` and `JOB_KEY`). |
| `BATCH_JOB_EXECUTION` | Physical execution attempt (stores `START_TIME`, `STATUS`, `EXIT_CODE`). |
| `BATCH_JOB_EXECUTION_PARAMS` | Parameters passed to the job execution (`STRING`, `DATE`, `LONG`). |
| `BATCH_STEP_EXECUTION` | Progress per step (stores `READ_COUNT`, `WRITE_COUNT`, `COMMIT_COUNT`, `SKIP_COUNT`). |
| `BATCH_STEP_EXECUTION_CONTEXT` | Checkpoint data for restarting failed steps. |

---

## 3. ShedLock distributed locking quick reference

### 1. PostgreSQL schema
```sql
CREATE TABLE shedlock (
    name VARCHAR(64) NOT NULL PRIMARY KEY,
    lock_until TIMESTAMP NOT NULL,
    locked_at TIMESTAMP NOT NULL,
    locked_by VARCHAR(255) NOT NULL
);
```

### 2. Lock configuration and usage
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
    // Executes on at most one server instance across the cluster.
}
```

---

## 4. Quartz clustered scheduling configuration (`application.yml`)

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

## Navigation and cheatsheet index

| Previous | Cheatsheet index | Next |
| :--- | :---: | ---: |
| [**Spring Boot packaging, Jib, and GraalVM native cheatsheet**](spring-boot-jib-docker-native.md) | [**All cheatsheets**](index.md) | [**GraphQL, gRPC, and WebSockets protocol cheatsheet**](graphql-grpc-websockets.md) |
