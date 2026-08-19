---
icon: lucide/refresh-cw
---

# 0034: Chunk-oriented processing: Readers, processors, and writers

When processing millions of records from a CSV file, relational database, or message queue, loading the entire dataset into memory causes fatal JVM `OutOfMemoryError` crashes. Conversely, committing a database transaction for every individual record creates extreme disk I/O bottlenecks.

Spring Batch solves this with **Chunk-Oriented Processing**: streaming items into memory individually, transforming them, and committing them in configurable, transaction-safe batches (chunks).

In this lesson, you will master the chunk processing lifecycle, implement `ItemReader`, `ItemProcessor`, and `ItemWriter`, chain transformations with `CompositeItemProcessor`, and configure transactional commit intervals.

---

## 1. The chunk-oriented processing lifecycle

Chunk processing structures work into a three-stage loop within a single transaction boundary:

``` mermaid
flowchart TD
    subgraph ChunkLoop["Chunk Execution Loop (e.g. Chunk Size = 100)"]
        Read["1. ItemReader.read()<br/><i>(Reads 1 item at a time until chunk is full)</i>"]
        Process["2. ItemProcessor.process(item)<br/><i>(Transforms or filters item)</i>"]
        Accumulate["3. Accumulate into List&lt;Output&gt;"]
        Write["4. ItemWriter.write(Chunk&lt;Output&gt;)<br/><i>(Writes all 100 items in 1 DB batch)</i>"]
        Commit["5. TransactionManager.commit()<br/><i>(Commits DB transaction & updates JobRepository checkpoint)</i>"]
        
        Read --> Process --> Accumulate
        Accumulate -->|Repeat 100 times| Read
        Accumulate -->|Chunk Buffer Full| Write --> Commit
    end
```

### The reader / processor / writer contract

| Interface | Method Signature | Behavior |
| :--- | :--- | :--- |
| **`ItemReader<I>`** | `I read()` | Returns the next item from the input stream. **Returns `null` when the data source is exhausted**, signaling step completion. |
| **`ItemProcessor<I, O>`** | `O process(I item)` | Transforms input item `I` into output item `O`. **Returning `null` discards the item**, excluding it from the written chunk. |
| **`ItemWriter<O>`** | `void write(Chunk<? extends O> chunk)` | Receives a `Chunk<O>` list and persists all items into the destination store in a single batch operation. |

---

## 2. Reading csv data: `FlatFileItemReader`

Let's build a reader that parses a CSV file (`customers.csv`) directly into immutable Java Records:

### `CustomerCsvRecord.java`
```java
package com.example.batch.dto;

import java.math.BigDecimal;

public record CustomerCsvRecord(
        Long id,
        String firstName,
        String lastName,
        String email,
        BigDecimal balance
) {}
```

### Reader bean configuration
```java
@Bean
public FlatFileItemReader<CustomerCsvRecord> customerCsvReader() {
    return new FlatFileItemReaderBuilder<CustomerCsvRecord>()
            .name("customerCsvReader")
            .resource(new ClassPathResource("data/customers.csv"))
            .linesToSkip(1) // Skip CSV Header line
            .delimited()
            .delimiter(",")
            .names("id", "firstName", "lastName", "email", "balance")
            .fieldSetMapper(new RecordFieldSetMapper<>(CustomerCsvRecord.class))
            .build();
}
```

---

## 3. Data transformation filtering: `ItemProcessor`

An `ItemProcessor` handles business validations and conversions. If an item fails validation, returning `null` filters it out cleanly:

```java
package com.example.batch.processor;

import com.example.batch.dto.CustomerCsvRecord;
import com.example.batch.entity.CustomerEntity;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

@Component
public class CustomerValidationProcessor implements ItemProcessor<CustomerCsvRecord, CustomerEntity> {

    @Override
    public CustomerEntity process(CustomerCsvRecord item) {
        // 1. Filter out inactive accounts with zero or negative balances
        if (item.balance().compareTo(BigDecimal.ZERO) <= 0) {
            return null; // Excluded from writing!
        }

        // 2. Transform into JPA Entity with normalized fields
        CustomerEntity entity = new CustomerEntity();
        entity.setExternalId(item.id());
        entity.setFullName(item.firstName().trim() + " " + item.lastName().trim());
        entity.setEmail(item.email().toLowerCase().trim());
        entity.setAccountBalance(item.balance());
        return entity;
    }
}
```

---

## 4. Persisting data: `JpaItemWriter`

Using `JpaItemWriter` persists the entire chunk in a single batch `EntityManager.merge()` operation:

```java
@Bean
public JpaItemWriter<CustomerEntity> customerJpaWriter(EntityManagerFactory entityManagerFactory) {
    return new JpaItemWriterBuilder<CustomerEntity>()
            .entityManagerFactory(entityManagerFactory)
            .build();
}
```

---

## 5. Wiring the complete chunk step

Assemble the Reader, Processor, and Writer into a chunk step with a commit interval of 250 items:

```java
package com.example.batch.config;

import com.example.batch.dto.CustomerCsvRecord;
import com.example.batch.entity.CustomerEntity;
import com.example.batch.processor.CustomerValidationProcessor;
import jakarta.persistence.EntityManagerFactory;
import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.database.JpaItemWriter;
import org.springframework.batch.item.file.FlatFileItemReader;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.PlatformTransactionManager;

@Configuration
public class CustomerIngestionJobConfig {

    @Bean
    public Job customerIngestionJob(JobRepository jobRepository, Step customerIngestionStep) {
        return new JobBuilder("customerIngestionJob", jobRepository)
                .start(customerIngestionStep)
                .build();
    }

    @Bean
    public Step customerIngestionStep(
            JobRepository jobRepository,
            PlatformTransactionManager transactionManager,
            FlatFileItemReader<CustomerCsvRecord> customerCsvReader,
            CustomerValidationProcessor customerProcessor,
            JpaItemWriter<CustomerEntity> customerJpaWriter) {

        return new StepBuilder("customerIngestionStep", jobRepository)
                // Chunk size = 250 records per database transaction commit
                .<CustomerCsvRecord, CustomerEntity>chunk(250, transactionManager)
                .reader(customerCsvReader)
                .processor(customerProcessor)
                .writer(customerJpaWriter)
                .build();
    }
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4: Chunk processing evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Batch 5)"]
        ChunkClass["org.springframework.batch.item.Chunk<T> Generics"]
        ClassMappers["BeanWrapperFieldSetMapper (JavaBeans)"]
        JdbcCursor["Standard JDBC / JPA Cursor Readers"]
    end

    subgraph SB4["Spring Boot 4.x (Batch 6)"]
        RecordMappers["Native RecordFieldSetMapper (Canonical Record Constructor)"]
        StatelessWriter["Hibernate 7 StatelessSession Batch ItemWriter"]
        KeysetReader["Spring Data Keyset Scroll Batch Readers"]
    end

    SB3 ==>|Chunk Performance Optimization| SB4
```

### Key differences and configuration comparison

| Chunk Processing Aspect | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Record Constructor Mapping** | Required manual `FieldSetMapper` implementation or reflection mapper. | **Native `RecordFieldSetMapper`**: Automatically binds CSV headers directly to Java Record component parameters. |
| **High-Volume JPA Writes** | Standard `JpaItemWriter` requiring 1st-level cache flushes to avoid memory leaks. | **`StatelessItemWriter`**: Bypasses Hibernate dirty checking and 1st-level cache for 3x faster bulk inserts. |
| **Database Pagination Reads** | `JpaPagingItemReader` with offset pagination (`LIMIT/OFFSET`). | **Keyset Pagination Readers**: Avoids deep page degradation using indexed column seeking. |

---

## 7. Primary sources and further reading

- [Spring Batch Reference Guide: Chunk-Oriented Processing](https://docs.spring.io/spring-batch/reference/step/chunk-oriented-processing.html), Transaction boundaries, commit intervals, and item streams.
- [Spring Batch Item Readers and Writers](https://docs.spring.io/spring-batch/reference/readers-and-writers.html), Guide to FlatFile, JDBC, JPA, Kafka, and Mongo implementations.
- [Vlad Mihalcea: High-Performance Batch Processing with Hibernate](https://vladmihalcea.com/how-to-batch-insert-and-update-statements-with-hibernate/), JDBC batch sizing and memory tuning.

---

## 8. Knowledge check and practice

??? question "Question 1: What does an `ItemReader` return when it reaches the end of the input dataset?"
    **Answer**: It returns `null`, which signals to the Spring Batch chunk execution framework that data reading is complete and the step can finish after processing remaining items.

??? question "Question 2: How can an `ItemProcessor` filter out invalid records so they are not written to the destination store?"
    **Answer**: By returning `null` from the `process(I item)` method, which excludes the item from the output chunk buffer.

??? question "Question 3: Why is chunk-based processing more memory-efficient and performant than processing records one-by-one or loading the whole file at once?"
    **Answer**: It maintains a small, constant memory footprint by streaming records in bounded chunks (e.g. 250 items) and minimizes database I/O by executing bulk inserts inside a single transaction commit per chunk.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0033: Spring Batch Core Architecture**](0033-spring-batch-architecture-jobrepository.md) | [**All Lessons**](index.md) | [ **0035: Fault Tolerance (Skip & Retry)**](0035-fault-tolerance-skip-retry-policies.md) |
