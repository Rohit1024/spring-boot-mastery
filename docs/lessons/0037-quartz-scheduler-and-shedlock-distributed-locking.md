---
icon: lucide/calendar-clock
---

# 0037: Task scheduling with Quartz and distributed locking with ShedLock

In modern cloud-native architectures, Spring Boot services are scaled horizontally across multiple Kubernetes Pods or cloud instances. When using Spring's built-in `@Scheduled(cron = "...")` annotation, **every single running instance executes the scheduled task concurrently**.

In critical business workflows, such as generating daily billing invoices or sending payment reminders, concurrent execution results in catastrophic race conditions, duplicate database writes, and customers being billed multiple times.

In this lesson, you will master distributed execution safety: implementing distributed locking with **ShedLock**, architecting clustered job orchestration with **Quartz Scheduler**, and integrating enterprise schedulers with **Spring Batch**.

---

## 1. The multi-instance scheduling collision problem

``` mermaid
flowchart TD
    subgraph K8sFleet["Kubernetes Production Fleet (3 Active Pods)"]
        Pod1["Pod 1 (@Scheduled 02:00 AM)"]
        Pod2["Pod 2 (@Scheduled 02:00 AM)"]
        Pod3["Pod 3 (@Scheduled 02:00 AM)"]
    end

    subgraph UnsafeExecution["❌ Without Distributed Locking"]
        Pod1 -->|Fires 02:00:00| Run1["Process Daily Invoices (Charge Customers)"]
        Pod2 -->|Fires 02:00:00| Run2["Process Daily Invoices (💥 DUPLICATE CHARGE!)"]
        Pod3 -->|Fires 02:00:00| Run3["Process Daily Invoices (💥 TRIPLICATE CHARGE!)"]
    end

    subgraph SafeExecution["✅ With ShedLock / Quartz Cluster"]
        LockDB[(Shared Lock Store: PostgreSQL / Redis)]
        
        Pod1 -->|1. Acquires Lock| LockDB
        LockDB -->|Lock Granted| RunSafe["Pod 1: Executes Task Alone 🛡️"]
        
        Pod2 -->|2. Attempts Lock| LockDB
        LockDB -.->|Lock Held by Pod 1| Skip2["Pod 2: Skips Execution Safely"]
        
        Pod3 -->|3. Attempts Lock| LockDB
        LockDB -.->|Lock Held by Pod 1| Skip3["Pod 3: Skips Execution Safely"]
    end

    UnsafeExecution ~~~ SafeExecution
```

---

## 2. Distributed locking with ShedLock

**ShedLock** ensures that your `@Scheduled` tasks execute **at most once** across your entire distributed server fleet by acquiring a shared database row or Redis key lock.

### Step 1: Database lock table schema (PostgreSQL)
```sql
CREATE TABLE shedlock (
    name VARCHAR(64) NOT NULL PRIMARY KEY,
    lock_until TIMESTAMP NOT NULL,
    locked_at TIMESTAMP NOT NULL,
    locked_by VARCHAR(255) NOT NULL
);
```

### Step 2: Configure `LockProvider` bean
```java
package com.example.scheduler.config;

import net.javacrumbs.shedlock.core.LockProvider;
import net.javacrumbs.shedlock.provider.jdbctemplate.JdbcTemplateLockProvider;
import net.javacrumbs.shedlock.spring.annotation.EnableSchedulerLock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.EnableScheduling;

import javax.sql.DataSource;

@Configuration
@EnableScheduling
@EnableSchedulerLock(defaultLockAtMostFor = "10m")
public class ShedLockConfig {

    @Bean
    public LockProvider lockProvider(DataSource dataSource) {
        return new JdbcTemplateLockProvider(
            JdbcTemplateLockProvider.Configuration.builder()
                .withJdbcTemplate(new JdbcTemplate(dataSource))
                .usingDbTime() // Uses database clock to prevent clock-drift issues across servers
                .build()
        );
    }
}
```

### Step 3: Annotating scheduled tasks
```java
package com.example.scheduler.tasks;

import net.javacrumbs.shedlock.spring.annotation.SchedulerLock;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class NightlyBillingScheduler {

    private static final Logger log = LoggerFactory.getLogger(NightlyBillingScheduler.class);

    // Runs every night at 2:00 AM
    @Scheduled(cron = "0 0 2 * * ?")
    @SchedulerLock(
        name = "NightlyBillingTask", 
        lockAtMostFor = "15m",  // Max time lock is held if node crashes midway
        lockAtLeastFor = "30s"  // Minimum lock duration to prevent re-execution if task finishes in 200ms
    )
    public void executeNightlyBilling() {
        log.info("Acquired distributed ShedLock: Executing billing run...");
        // Business logic or Spring Batch JobLauncher execution...
    }
}
```

---

## 3. Clustered enterprise scheduling with Quartz

While ShedLock coordinates simple `@Scheduled` methods, **Quartz Scheduler** provides full enterprise job management: dynamic runtime schedule creation, stateful jobs, cluster failover, and detailed missed-fire handling.

### Quartz domain hierarchy

``` mermaid
flowchart TD
    Scheduler["Quartz Scheduler Engine"]
    
    JobDetail["JobDetail<br/><i>(Job identity & JobExecutionContext)</i>"]
    Trigger["CronTrigger / SimpleTrigger<br/><i>(Defines firing schedule & misfire policy)</i>"]
    JobClass["Job Implementation Class<br/><i>(implements org.quartz.Job)</i>"]
    
    Scheduler --> Trigger
    Scheduler --> JobDetail
    JobDetail --> JobClass
    
    subgraph QuartzClusterDB["Shared Relational Schema (QRTZ_* Tables)"]
        Q_TRIGGERS["QRTZ_TRIGGERS"]
        Q_LOCKS["QRTZ_LOCKS"]
        Q_FIRED["QRTZ_FIRED_TRIGGERS"]
    end
    
    Scheduler <--> QuartzClusterDB
```

---

## 4. Quartz Spring Boot configuration (`applicationyml`)

```yaml
spring:
  quartz:
    job-store-type: jdbc
    jdbc:
      initialize-schema: always # or 'never' in production
    properties:
      org.quartz.scheduler.instanceName: EnterpriseQuartzClusteredScheduler
      org.quartz.scheduler.instanceId: AUTO # Auto-generates unique pod instance ID
      org.quartz.jobStore.isClustered: true
      org.quartz.jobStore.clusterCheckinInterval: 20000 # Heartbeat check-in 20s
      org.quartz.jobStore.misfireThreshold: 60000
```

### Implementing a Quartz job bridging to Spring batch

```java
package com.example.scheduler.quartz;

import org.quartz.DisallowConcurrentExecution;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.JobParameters;
import org.springframework.batch.core.JobParametersBuilder;
import org.springframework.batch.core.launch.JobLauncher;
import org.springframework.scheduling.quartz.QuartzJobBean;
import org.springframework.stereotype.Component;

import java.util.Date;

@Component
@DisallowConcurrentExecution // Prevents Quartz from firing multiple instances of THIS job on the cluster
public class BatchJobLauncherQuartzJob extends QuartzJobBean {

    private static final Logger log = LoggerFactory.getLogger(BatchJobLauncherQuartzJob.class);
    
    private final JobLauncher jobLauncher;
    private final Job customerIngestionJob;

    public BatchJobLauncherQuartzJob(JobLauncher jobLauncher, Job customerIngestionJob) {
        this.jobLauncher = jobLauncher;
        this.customerIngestionJob = customerIngestionJob;
    }

    @Override
    protected void executeInternal(JobExecutionContext context) throws JobExecutionException {
        try {
            log.info("Quartz cluster trigger firing Spring Batch Job...");
            JobParameters params = new JobParametersBuilder()
                    .addDate("quartzFireTime", new Date())
                    .addString("triggerId", context.getTrigger().getKey().getName())
                    .toJobParameters();

            jobLauncher.run(customerIngestionJob, params);
        } catch (Exception ex) {
            log.error("Failed to execute Spring Batch job from Quartz", ex);
            throw new JobExecutionException(ex);
        }
    }
}
```

---

## 5. Wiring Quartz `JobDetail` and `Trigger` beans

```java
package com.example.scheduler.config;

import com.example.scheduler.quartz.BatchJobLauncherQuartzJob;
import org.quartz.*;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class QuartzScheduleConfig {

    @Bean
    public JobDetail batchJobDetail() {
        return JobBuilder.newJob(BatchJobLauncherQuartzJob.class)
                .withIdentity("batchIngestionJobDetail", "BATCH_JOBS")
                .storeDurably()
                .requestRecovery(true) // If node dies while executing, another cluster node re-executes it!
                .build();
    }

    @Bean
    public Trigger batchJobTrigger(JobDetail batchJobDetail) {
        return TriggerBuilder.newTrigger()
                .forJob(batchJobDetail)
                .withIdentity("batchIngestionTrigger", "BATCH_TRIGGERS")
                // Every day at 3:00 AM UTC
                .withSchedule(CronScheduleBuilder.cronSchedule("0 0 3 * * ?")
                        .withMisfireHandlingInstructionDoNothing()) // Skip missed triggers on downtime
                .build();
    }
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4: Scheduling evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        ShedLock4["ShedLock 4.x / 5.x JDBC Providers"]
        QuartzJdbc["Clustered Quartz with javax/jakarta Relational Scripts"]
        PlatformScheduler["ScheduledAnnotationBeanPostProcessor (Platform Threads)"]
    end

    subgraph SB4["Spring Boot 4.x"]
        LoomScheduling["Virtual-Thread Native @Scheduled Dispatch"]
        NativeRedisLock["Spring Data Redis Distributed Lock Abstraction"]
        AOTQuartz["AOT Pre-Compiled Quartz Job Registrations"]
    end

    SB3 ==>|Cloud Orchestration & Loom Schedulers| SB4
```

### Key differences and configuration comparison

| Scheduling Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Scheduler Thread Model** | Single background thread or fixed thread pool (`spring.task.scheduling.pool.size=5`). | **Virtual Thread Dispatcher**: Every scheduled task fires on an isolated, lightweight Virtual Thread. |
| **Distributed Lock Abstraction** | Relied on external third-party libraries (ShedLock). | **Native Distributed Locking Starter**: Built-in declarative lock abstraction across Redis, Postgres, and Consul. |
| **Quartz AOT / Native Image** | Required reflection metadata registration for all Quartz Job classes. | **AOT Pre-Registered Quartz Beans**: Direct zero-reflection native compilation. |

---

## 7. Primary sources and further reading

- [ShedLock GitHub Repository & Documentation](https://github.com/lukas-krecan/ShedLock), Multi-node distributed lock providers and timing parameters.
- [Quartz Enterprise Job Scheduler Documentation](http://www.quartz-scheduler.org/documentation/), Clustered configuration and misfire policies.
- [Spring Boot Task Execution and Scheduling](https://docs.spring.io/spring-boot/reference/features/task-execution-and-scheduling.html), Configuring task executors and schedulers.

---

## 8. Knowledge check and practice

??? question "Question 1: What is the risk of using `@Scheduled` without ShedLock in a horizontally scaled microservice deployment?"
    **Answer**: All service replicas/pods will execute the scheduled task simultaneously at the trigger timestamp, resulting in concurrent race conditions, duplicate database writes, and resource exhaustion.

??? question "Question 2: In ShedLock, why is `lockAtLeastFor` critical when a scheduled task finishes execution very quickly?"
    **Answer**: If a task finishes in 100ms, without `lockAtLeastFor`, the lock is immediately released and another pod whose system clock is slightly behind might re-acquire the lock and execute the task a second time.

??? question "Question 3: What does the Quartz `requestRecovery(true)` configuration provide in a clustered environment?"
    **Answer**: If the server node running the active job crashes midway, surviving cluster nodes automatically detect the failure and re-execute the recovered job.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0036: Multi-Threaded Steps & Partitioning**](0036-multithreaded-steps-and-partitioning.md) | [**All Lessons**](index.md) | [ **0038: Spring for GraphQL**](0038-spring-graphql-schema-queries-mutations.md) |

🎉 **Congratulations on completing Module 7: Batch Processing & Scheduling!**
