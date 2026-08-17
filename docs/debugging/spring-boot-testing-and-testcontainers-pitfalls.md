---
icon: lucide/bug
---

# Troubleshooting Spring Boot Testing & Testcontainers Pitfalls

A robust test suite is the single greatest asset for production software, but poorly architected tests can severely degrade developer velocity. Test suites that take 45 minutes to run, crash unpredictably in CI/CD pipelines, or pass locally against H2 only to fail in production PostgreSQL create severe bottlenecks.

This playbook provides root-cause diagnostic workflows, reproducible scenarios, and production-tested solutions for Spring Boot testing, Mockito, MockMvc, and Testcontainers failures.

---

## 1. Diagnostic Decision Tree

``` mermaid
flowchart TD
    Start["Testing Failure Detected"] --> ErrType{"Identify Failure Category"}

    ErrType -->|Test suite takes 30+ minutes & re-boots Spring 50 times| CacheErr["1. Context Cache Invalidation"]
    ErrType -->|DockerClientException: Could not find valid Docker environment| DockerErr["2. Testcontainers Daemon Failure"]
    ErrType -->|Tests pass on H2 but crash on PostgreSQL production| DialectErr["3. H2 Dialect & Feature Incompatibility"]

    CacheErr --> FixCache["Remove @DirtiesContext & standardize @MockitoBean definitions"]
    DockerErr --> FixDocker["Mount /var/run/docker.sock in CI or configure DOCKER_HOST"]
    DialectErr --> FixDialect["Migrate tests to real PostgreSQL using @ServiceConnection"]
```

---

## 2. Issue 1: Test Execution Slowness & Context Cache Thrashing

### Symptoms & Root Cause
A test suite containing 100 test classes takes over 25 minutes to execute. Looking at logs, Spring's banner prints dozens of times, indicating the `ApplicationContext` is being repeatedly destroyed and recreated.

``` mermaid
flowchart TD
    subgraph AntiPattern["❌ Context Thrashing Anti-Pattern"]
        TestA["TestClassA (@MockitoBean OrderService)"]
        Dirties["@DirtiesContext / Unique Mock Config"]
        TestB["TestClassB (@MockitoBean PaymentService)"]
        
        TestA --> Dirties -->|Context Cache Evicted!| Rebuild["Re-boots full Spring Context (Slow!)"]
        Rebuild --> TestB
    end

    subgraph BestPractice["✅ Reused Cached Context"]
        Test1["TestClass1"]
        SharedContext[("Shared Cached ApplicationContext")]
        Test2["TestClass2"]
        
        Test1 --> SharedContext -->|Zero Reboots! Instant Execution!| Test2
    end

    AntiPattern ~~~ BestPractice
```

### Resolution
1. **Eliminate `@DirtiesContext`**: Rely on transactional rollbacks (`@Transactional` on test classes) to clean database state rather than destroying the entire JVM Spring context.
2. **Standardize Context Overrides**: Group beans into a shared base test configuration rather than declaring unique `@MockitoBean` configurations in every individual test file.

---

## 3. Issue 2: Testcontainers Docker Daemon Connection Failure in CI/CD

### Symptoms & Error Log
Tests execute successfully on local developer laptops, but fail immediately in GitLab CI, GitHub Actions, or Jenkins with:

```text
org.testcontainers.containers.ContainerLaunchException: Container startup failed
Caused by: com.github.dockerjava.api.exception.DockerClientException: 
Could not find a valid Docker environment. Please see logs and check configuration
```

### Root Cause
The CI/CD runner container lacks permissions or access to the host Docker daemon socket (`/var/run/docker.sock`).

### Resolution
In your GitHub Actions workflow (`.github/workflows/ci.yml`), ensure Docker-in-Docker is active or mount the socket:

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up JDK 21
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
      - name: Run Tests with Testcontainers
        run: mvn clean test
```
*(On local Docker Desktop, ensure "Allow default Docker socket" is enabled in settings).*

---

## 4. Issue 3: MockMvc JSON Path Assertion Failures on Numbers

### Symptoms & Error Log
```text
java.lang.AssertionError: JSON path "$.totalAmount" expected:<1200.00> but was:<1200.0>
```

### Root Cause
Jackson serializes `BigDecimal` with trailing zeros stripped or formatted as double floating-point numbers unless explicit formatting or Hamcrest `closeTo` / `comparesEqualTo` is used.

### Resolution
Use Hamcrest numeric matchers:

```java
// ✅ MATCHES NUMERIC VALUE REGARDLESS OF TRAILING ZERO FORMATTING
mockMvc.perform(get("/api/v1/orders/1"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.totalAmount", closeTo(1200.00, 0.001)));
```

---

## 🧭 Navigation & Diagnostic Playbooks

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Troubleshooting Prometheus & OpenTelemetry**](prometheus-scraping-and-opentelemetry-collector-pitfalls.md) | [**All Debugging Guides**](index.md) | [➡️ **Troubleshooting Redis Caching & Kafka Lag**](redis-cache-stampede-and-kafka-consumer-lag.md) |
