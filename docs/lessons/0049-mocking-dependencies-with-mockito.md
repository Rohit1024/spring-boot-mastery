---
icon: lucide/shield-check
---

# 0049: Mocking Dependencies with Mockito (`@Mock`, `@InjectMocks`, `verify`)

Unit tests must test business logic in strict isolation. If a unit test directly calls a real PostgreSQL database, sends real Stripe API charges, or connects to Kafka, it ceases to be a unit test—it becomes slow, flaky, and prone to environmental failures.

**Mockito** is the de facto mocking framework in the Java ecosystem. It dynamically intercepts collaborator method invocations, returns pre-programmed stubs, and verifies interaction contracts.

In this lesson, you will master configuring Mockito with JUnit 5, stubbing method calls with `when()`, verifying collaborator interactions with `verify()`, and capturing arguments using `ArgumentCaptor`.

---

## 1. Mockito Proxy Interception Architecture

``` mermaid
flowchart TD
    subgraph TestExecution["JUnit 5 Test Execution"]
        UnitTest["OrderServiceTest"]
    end

    subgraph TargetService["Target Class Under Test"]
        OrderService["OrderService (@InjectMocks)"]
    end

    subgraph MockProxies["ByteBuddy Dynamic Mocks (@Mock)"]
        PaymentMock["PaymentGateway (Dynamic Mock Proxy)"]
        RepoMock["OrderRepository (Dynamic Mock Proxy)"]
    end

    subgraph RealWorld["Real External Infrastructure"]
        RealDB[("PostgreSQL Database")]
        Stripe["Stripe HTTP Gateway"]
    end

    UnitTest -->|1. Configures Stubs via when/thenReturn| PaymentMock & RepoMock
    UnitTest -->|2. Calls orderService.processOrder| OrderService
    OrderService -->|3. Intercepted by Proxy| PaymentMock & RepoMock
    PaymentMock -.->|Blocked! Zero real network calls| Stripe
    RepoMock -.->|Blocked! Zero real database queries| RealDB
    UnitTest -->|4. Verifies interactions via verify| RepoMock
```

---

## 2. Core Mockito Annotations with JUnit 5

Enable Mockito's annotation processor using `@ExtendWith(MockitoExtension.class)`:

```java
package com.example.ecommerce.order;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.*;
import org.mockito.junit.jupiter.MockitoExtension;
import java.math.BigDecimal;
import java.util.Optional;

import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class OrderServiceTest {

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private PaymentGateway paymentGateway;

    @Mock
    private NotificationService notificationService;

    @InjectMocks
    private OrderService orderService; // Mockito automatically injects mocks into constructor!

    @Test
    void shouldSuccessfullyProcessOrder() {
        // Given
        Order pendingOrder = new Order(101L, new BigDecimal("75.00"), OrderStatus.PENDING);
        PaymentReceipt receipt = new PaymentReceipt("TXN-999", true);

        // Stubbing Collaborators:
        when(orderRepository.findById(101L)).thenReturn(Optional.of(pendingOrder));
        when(paymentGateway.charge(any(BigDecimal.class))).thenReturn(receipt);
        when(orderRepository.save(any(Order.class))).thenAnswer(invocation -> invocation.getArgument(0));

        // When
        Order result = orderService.processOrder(101L);

        // Then (Assertions & Verifications)
        assertThat(result.getStatus()).isEqualTo(OrderStatus.COMPLETED);

        // Verify collaborator interaction contracts:
        verify(orderRepository, times(1)).findById(101L);
        verify(paymentGateway, times(1)).charge(new BigDecimal("75.00"));
        verify(orderRepository, times(1)).save(pendingOrder);
        verify(notificationService, times(1)).sendConfirmationEmail(any());
        verifyNoMoreInteractions(paymentGateway);
    }
}
```

---

## 3. Exception Stubbing & Verification Variations

### 1. Simulating Collaborator Failures (`thenThrow` / `doThrow`)
```java
@Test
void shouldFailOrderWhenPaymentDeclined() {
    when(orderRepository.findById(101L)).thenReturn(Optional.of(new Order(101L, new BigDecimal("50.00"), OrderStatus.PENDING)));
    
    // Stub payment failure:
    when(paymentGateway.charge(any()))
            .thenThrow(new PaymentDeclinedException("Card expired"));

    assertThatThrownBy(() -> orderService.processOrder(101L))
            .isInstanceOf(PaymentDeclinedException.class)
            .hasMessage("Card expired");

    // Verify email was NEVER sent when payment fails:
    verify(notificationService, never()).sendConfirmationEmail(any());
}
```

### 2. Spying on Real Instances (`@Spy`)
A `@Spy` wraps a real class instance, allowing selective stubbing while delegating unstubbed methods to the real implementation:

```java
@Spy
private TaxCalculator taxCalculator = new TaxCalculator(); // Real object

@Test
void shouldCalculateRealTaxUnlessOverridden() {
    // Unstubbed methods execute real arithmetic logic
    BigDecimal tax = taxCalculator.calculateTax(new BigDecimal("100.00"));
    assertThat(tax).isEqualByComparingTo(new BigDecimal("8.00"));
}
```

---

## 4. Capturing Arguments with `ArgumentCaptor`

`ArgumentCaptor` allows inspecting the exact parameters passed to a mock during execution:

```java
@Captor
private ArgumentCaptor<Order> orderCaptor;

@Test
void shouldPersistOrderWithUpdatedTimestamp() {
    Order order = new Order(101L, new BigDecimal("100.00"), OrderStatus.PENDING);
    when(orderRepository.findById(101L)).thenReturn(Optional.of(order));
    when(paymentGateway.charge(any())).thenReturn(new PaymentReceipt("TXN-1", true));

    orderService.processOrder(101L);

    // Capture the argument passed to orderRepository.save():
    verify(orderRepository).save(orderCaptor.capture());
    Order savedOrder = orderCaptor.getValue();

    assertThat(savedOrder.getProcessedAt()).isNotNull();
    assertThat(savedOrder.getStatus()).isEqualTo(OrderStatus.COMPLETED);
}
```

---

## 5. Mockito Anti-Patterns to Avoid

| Anti-Pattern | Why It Is Problematic | Proper Approach |
| :--- | :--- | :--- |
| **Mocking Data Objects (DTOs / Records)** | Mocking simple getters/setters creates unnecessary boilerplate and hides bugs. | Instantiate real Java POJOs, DTOs, or Records directly. |
| **Over-Verifying Every Method Call** | Asserting every trivial interaction makes tests brittle to harmless internal refactorings. | Only verify side-effects (`.save()`, `.sendEmail()`) and external boundaries. |
| **Mocking What You Don't Own** | Mocking third-party HTTP client libraries leads to inaccurate assumptions. | Wrap third-party SDKs in an adapter interface and mock the adapter. |

---

## 6. Spring Boot 3 vs Spring Boot 4: Mocking Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.0–3.3 (Legacy Spring Test)"]
        OldMockBean["@MockBean & @SpyBean (Spring Boot Test Annotations)"]
        ContextPollution["Replaces Bean in Spring ApplicationContext"]
        SlowCacheMiss["Causes Spring Context Cache Miss & Re-initialization"]
    end

    subgraph SB4["Spring Boot 3.4+ & 4.x (Unified Spring Framework 6.2+)"]
        NewMockitoBean["@MockitoBean & @MockitoSpyBean (Core Spring Framework)"]
        StandardizedMocking["Standardized Mockito integration without Spring Boot coupling"]
        OptimizedCache["Optimized TestContextManager Bean Replacement Engine"]
    end

    SB3 ==>|Deprecation of @MockBean in favor of @MockitoBean| SB4
```

### Key Differences & Configuration Comparison

| Mocking Feature | Spring Boot 3.0–3.3 | Spring Boot 3.4+ & 4.x |
| :--- | :--- | :--- |
| **Spring Context Mocking** | Used `@MockBean` and `@SpyBean` from `org.springframework.boot.test.mock.mockito`. | **`@MockitoBean` & `@MockitoSpyBean`**: Moved to core Spring Framework (`org.springframework.test.context.bean.override.mockito`). `@MockBean` is officially deprecated. |
| **Mock Maker Engine** | ByteBuddy Subclass mock maker (required mock-maker-inline for final classes). | **ByteBuddy Inline Mock Maker by Default**: Seamlessly mocks `final` classes, `final` methods, and Java 21 records out of the box. |

---

## 7. Primary Sources & Further Reading

- [Mockito Official Documentation](https://javadoc.io/doc/org.mockito/mockito-core/latest/org/mockito/Mockito.html) — Stubs, spies, argument matchers, and BDD Mockito.
- [Spring Framework 6.2+ `@MockitoBean` Guide](https://docs.spring.io/spring-framework/reference/testing/testcontext-framework/bean-overriding/mockito.html) — Official documentation on modern bean overriding in tests.

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the difference between `@Mock` and `@Spy` in Mockito?"
    **Answer**: `@Mock` creates a pure dynamic proxy where all methods return default empty values (null, 0, false) unless explicitly stubbed; `@Spy` wraps a real object instance and executes real methods unless a specific method is stubbed.

??? question "Question 2: What happens if an un-stubbed method is called on a `@Mock` object?"
    **Answer**: Mockito returns the default empty value for that method's return type (`null` for objects, `false` for booleans, `0` for numbers, empty collections for lists/sets).

??? question "Question 3: Why should you migrate from `@MockBean` to `@MockitoBean` in Spring Boot 3.4+ and Spring Boot 4?"
    **Answer**: `@MockBean` is deprecated; `@MockitoBean` is the modern first-class replacement provided by core Spring Framework 6.2+ with improved context caching efficiency.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0048: Unit Testing with JUnit 5 & AssertJ**](0048-unit-testing-junit-5-assertj.md) | [**All Lessons**](index.md) | [➡️ **0050: REST API Testing with MockMvc**](0050-integration-testing-rest-apis-mockmvc.md) |
