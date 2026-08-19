---
icon: lucide/check-circle-2
---

# 0048: Unit testing with JUnit 5 and AssertJ

High-velocity engineering teams rely on fast, deterministic unit tests to catch regressions before code ever touches a staging environment. If tests are slow, flaky, or difficult to read, developer productivity collapses.

**JUnit 5** (Jupiter) is the modern standard testing framework for Java, featuring modular architecture, rich parameterization, and nested hierarchies. Paired with **AssertJ**, it provides fluent, human-readable assertions that produce crystal-clear diagnostic failure messages.

In this lesson, you will master writing unit tests using JUnit 5 annotations, executing parameterized test suites, and structuring expressive assertions with AssertJ.

---

## 1. JUnit 5 test execution lifecycle

``` mermaid
flowchart TD
    subgraph SuiteSetup["1. Test Class Initialization"]
        BeforeAll["@BeforeAll: Static setup (Runs once per class)"]
    end

    subgraph TestIteration["2. Per-Test Execution Cycle"]
        BeforeEach["@BeforeEach: Reset state / Initialize fixtures"]
        TestExec["@Test / @ParameterizedTest execution"]
        AfterEach["@AfterEach: Clean up mocks / Reset context"]
        
        BeforeEach --> TestExec --> AfterEach
    end

    subgraph SuiteTeardown["3. Test Class Teardown"]
        AfterAll["@AfterAll: Static cleanup (Runs once per class)"]
    end

    BeforeAll --> BeforeEach
    AfterEach -->|Next Test Method| BeforeEach
    AfterEach -->|All Tests Completed| AfterAll
```

---

## 2. Core JUnit 5 annotations structure

A production unit test isolates pure business logic without spinning up Spring's heavyweight `ApplicationContext`:

```java
package com.example.ecommerce.order;

import org.junit.jupiter.api.*;
import java.math.BigDecimal;
import static org.assertj.core.api.Assertions.*;

@DisplayName("Order Pricing & Discount Calculation Tests")
class OrderPricingCalculatorTest {

    private OrderPricingCalculator calculator;

    @BeforeEach
    void setUp() {
        calculator = new OrderPricingCalculator();
    }

    @Test
    @DisplayName("Should apply 10% discount for orders exceeding $100")
    void shouldApplyDiscountForLargeOrders() {
        // Given
        BigDecimal orderTotal = new BigDecimal("150.00");
        CustomerTier tier = CustomerTier.VIP;

        // When
        BigDecimal discountedPrice = calculator.calculateFinalPrice(orderTotal, tier);

        // Then (AssertJ Fluent Assertion)
        assertThat(discountedPrice)
                .isNotNull()
                .isEqualByComparingTo(new BigDecimal("135.00"));
    }
}
```

---

## 3. Parameterized testing with `@ParameterizedTest`

Instead of duplicating test methods for different input combinations, use parameterized tests:

### 1. `@ValueSource` `@CsvSource`
```java
@ParameterizedTest(name = "Tier {0} on ${1} should yield final price ${2}")
@CsvSource({
    "STANDARD, 100.00, 100.00",
    "SILVER,   100.00, 95.00",
    "GOLD,     100.00, 90.00",
    "VIP,      100.00, 80.00"
})
void shouldCalculateTierDiscounts(CustomerTier tier, BigDecimal subtotal, BigDecimal expectedTotal) {
    BigDecimal result = calculator.calculateFinalPrice(subtotal, tier);
    assertThat(result).isEqualByComparingTo(expectedTotal);
}
```

### 2. Complex objects via `@MethodSource`
```java
static Stream<Arguments> provideInvalidOrders() {
    return Stream.of(
        Arguments.of(null, "Order subtotal cannot be null"),
        Arguments.of(new BigDecimal("-10.00"), "Order subtotal cannot be negative")
    );
}

@ParameterizedTest
@MethodSource("provideInvalidOrders")
void shouldRejectInvalidSubtotals(BigDecimal invalidSubtotal, String expectedError) {
    assertThatThrownBy(() -> calculator.calculateFinalPrice(invalidSubtotal, CustomerTier.STANDARD))
            .isInstanceOf(IllegalArgumentException.class)
            .hasMessageContaining(expectedError);
}
```

---

## 4. Fluent assertions with AssertJ

AssertJ transforms error diagnostics by providing descriptive, chained assertions:

### 1. Collection object property extraction
```java
List<OrderItem> items = order.getItems();

// Verify collection properties fluently:
assertThat(items)
        .hasSize(3)
        .extracting(OrderItem::getSku, OrderItem::getQuantity)
        .containsExactlyInAnyOrder(
            tuple("SKU-APPLE", 2),
            tuple("SKU-BANANA", 5),
            tuple("SKU-ORANGE", 1)
        );
```

### 2. Deep object comparison (`usingrecursivecomparison`)
```java
Customer actual = customerService.findById(1L);
Customer expected = new Customer(1L, "Alice", "alice@example.com");

// Compares all fields recursively, ignoring generated timestamp:
assertThat(actual)
        .usingRecursiveComparison()
        .ignoringFields("createdAt", "updatedAt")
        .isEqualTo(expected);
```

---

## 5. Hierarchical context with `@Nested`

Group related test scenarios logically using `@Nested` test classes to model Behavior-Driven Development (BDD) specifications:

```java
@DisplayName("Bank Account Operations")
class BankAccountTest {

    private BankAccount account;

    @BeforeEach
    void init() { account = new BankAccount(100.0); }

    @Nested
    @DisplayName("When withdrawing funds")
    class WithdrawalTests {

        @Test
        @DisplayName("Should reduce balance when funds are sufficient")
        void shouldDeductBalance() {
            account.withdraw(40.0);
            assertThat(account.getBalance()).isEqualTo(60.0);
        }

        @Test
        @DisplayName("Should throw InsufficientFundsException when overdraft attempted")
        void shouldThrowOnOverdraft() {
            assertThatThrownBy(() -> account.withdraw(150.0))
                    .isInstanceOf(InsufficientFundsException.class)
                    .hasMessage("Insufficient balance for withdrawal");
        }
    }
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4: Testing AssertJ evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (JUnit 5.10 / AssertJ 3.25)"]
        JupiterEngine3["JUnit Jupiter 5.10 Engine"]
        ClassicAssertions["AssertJ 3.x Assertions"]
        ParallelOptIn["Opt-in Parallel Test Execution via junit-platform.properties"]
    end

    subgraph SB4["Spring Boot 4.x (JUnit 5.12+ / AssertJ 4.0)"]
        JupiterEngine4["JUnit 5.12 with Native Virtual Thread Test Runners"]
        AssertJ4["AssertJ 4.0 with Java Record & Sealed Class Pattern Matching"]
        AutoParallelContext["Concurrent Test Class Execution with Zero Context Pollution"]
    end

    SB3 ==>|Virtual Thread Test Engines & Pattern Matching Assertions| SB4
```

### Key differences and configuration comparison

| Testing Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **AssertJ Pattern Matching** | Traditional `.extracting()` and reflection assertions. | **Record & Sealed Type Assertions**: Direct exhaustive pattern matching assertions without reflection. |
| **Concurrent Test Execution** | Test methods ran on standard OS thread pools. | **Virtual Thread Test Execution**: JUnit Jupiter runs concurrent tests on Virtual Threads for 5x faster IO test suites. |
| **Exception Assertions** | `assertThatThrownBy()` and `assertThatExceptionOfType()`. | **Enhanced Root Cause Chaining**: `.hasRootCauseInstanceOf()` with deep suppression inspection. |

---

## 7. Primary sources and further reading

- [JUnit 5 User Guide](https://junit.org/junit5/docs/current/user-guide/), Complete specification for Jupiter extensions, lifecycle, and parallel execution.
- [AssertJ Core Documentation](https://assertj.github.io/doc/), Fluent assertions for collections, maps, dates, and recursive comparisons.
- [Martin Fowler: Practical Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html), Balancing unit, integration, and UI testing layers.

---

## 8. Knowledge check and practice

??? question "Question 1: Why is AssertJ's `assertThat(actual).isEqualTo(expected)` superior to JUnit's `assertEquals(expected, actual)`?"
    **Answer**: AssertJ enforces a consistent `(actual)` input format, provides auto-completion via IDE method chaining, and generates highly detailed diagnostic error messages showing exact field-level diffs.

??? question "Question 2: What is the purpose of `@Nested` in JUnit 5?"
    **Answer**: It allows grouping related test cases into hierarchical inner classes with their own `@BeforeEach` setup methods, creating expressive, readable BDD-style test specifications.

??? question "Question 3: How does `@CsvSource` supply data to a `@ParameterizedTest`?"
    **Answer**: It accepts an array of comma-separated string literals representing arguments, automatically converting strings into primitive types, BigDecimals, or enums for each test execution.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0047: OpenTelemetry & OTLP Collectors**](0047-opentelemetry-otel-tracing-and-otlp-collectors.md) | [**All Lessons**](index.md) | [ **0049: Mocking Dependencies with Mockito**](0049-mocking-dependencies-with-mockito.md) |
