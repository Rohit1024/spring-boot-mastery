---
icon: lucide/flask-conical
---

# Enterprise Testing & Testcontainers Cheatsheet

A rapid reference guide for JUnit 5 lifecycle annotations, AssertJ fluent assertions, Mockito stubbing/verification, Spring Boot `@WebMvcTest` slices, and Testcontainers database integration.

---

## 1. JUnit 5 & AssertJ Quick Reference

### Parameterized Tests:
```java
@ParameterizedTest
@CsvSource({
    "STANDARD, 100.0, 100.0",
    "VIP,      100.0, 80.0"
})
void testDiscounts(CustomerTier tier, BigDecimal subtotal, BigDecimal expected) {
    assertThat(calculator.calculate(subtotal, tier)).isEqualByComparingTo(expected);
}
```

### Fluent AssertJ Assertions:
```java
// Collections & Extraction:
assertThat(orders)
        .hasSize(2)
        .extracting(Order::getId, Order::getStatus)
        .contains(tuple(1L, OrderStatus.COMPLETED));

// Exceptions:
assertThatThrownBy(() -> account.withdraw(999.0))
        .isInstanceOf(InsufficientFundsException.class)
        .hasMessageContaining("Insufficient balance");
```

---

## 2. Mockito Stubbing & Verification

```java
@ExtendWith(MockitoExtension.class)
class OrderServiceTest {
    @Mock private OrderRepository orderRepository;
    @Mock private PaymentGateway paymentGateway;
    @InjectMocks private OrderService orderService;

    @Test
    void testOrderWorkflow() {
        when(orderRepository.findById(1L)).thenReturn(Optional.of(new Order(1L)));
        when(paymentGateway.charge(any())).thenReturn(new Receipt("TXN-1", true));

        orderService.processOrder(1L);

        verify(orderRepository, times(1)).save(any(Order.class));
        verify(paymentGateway, times(1)).charge(any());
        verifyNoMoreInteractions(paymentGateway);
    }
}
```

---

## 3. Spring Boot Web Slicing (`@WebMvcTest`)

```java
@WebMvcTest(OrderRestController.class)
class OrderRestControllerTest {
    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;
    @MockitoBean private OrderService orderService; // Spring Boot 3.4+ / 4.x

    @Test
    void shouldCreateOrder() throws Exception {
        when(orderService.createOrder(any())).thenReturn(new OrderResponse(1L));

        mockMvc.perform(post("/api/v1/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(new CreateOrderRequest("CUST-1"))))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.id").value(1));
    }
}
```

---

## 4. Testcontainers with `@ServiceConnection` (Spring Boot 3.1+)

```java
@DataJpaTest
@Testcontainers
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class OrderRepositoryTest {
    @Container
    @ServiceConnection
    static PostgreSQLContainer<?> postgres = new PostgreSQLContainer<>("postgres:16-alpine");

    @Autowired private OrderRepository orderRepository;

    @Test
    void testRealDatabasePersistence() {
        Order saved = orderRepository.save(new Order("CUST-1", BigDecimal.TEN));
        assertThat(orderRepository.findById(saved.getId())).isPresent();
    }
}
```

---

## 🧭 Navigation & Cheatsheet Index

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Prometheus, Grafana & OTel Cheatsheet**](prometheus-grafana-opentelemetry.md) | [**All Cheatsheets**](index.md) | [➡️ **Redis Caching & Kafka Cheatsheet**](redis-caching-and-kafka-messaging.md) |
