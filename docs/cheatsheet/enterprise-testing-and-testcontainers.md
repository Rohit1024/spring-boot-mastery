---
icon: lucide/flask-conical
---

# Enterprise testing and Testcontainers cheatsheet

Reference for JUnit 5 lifecycle annotations, AssertJ assertions, Mockito verification, Spring Boot `@WebMvcTest` slices, and Testcontainers database tests.

---

## 1. JUnit 5 and AssertJ quick reference

### Parameterized tests
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

### Fluent AssertJ assertions
```java
// Collections and extraction:
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

## 2. Mockito stubbing and verification

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

## 3. Spring Boot web slicing with `@WebMvcTest`

```java
@WebMvcTest(OrderRestController.class)
class OrderRestControllerTest {
    @Autowired private MockMvc mockMvc;
    @Autowired private ObjectMapper objectMapper;
    @MockitoBean private OrderService orderService; // Spring Boot 3.4+ and 4.x

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

## Navigation and cheatsheet index

| Previous | Cheatsheet index | Next |
| :--- | :---: | ---: |
| [**Prometheus, Grafana, and OpenTelemetry cheatsheet**](prometheus-grafana-opentelemetry.md) | [**All cheatsheets**](index.md) | [**Redis caching and Kafka cheatsheet**](redis-caching-and-kafka-messaging.md) |
