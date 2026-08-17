---
icon: lucide/globe
---

# 0050: Integration Testing REST APIs with `@SpringBootTest` & `MockMvc`

Unit tests prove that individual Java classes work in isolation, but they cannot verify that HTTP serialization, `@Valid` bean constraint annotations, Spring Security filter chains, or `@RestControllerAdvice` exception handlers function correctly together.

**Spring MVC Test** (`MockMvc`) enables high-speed integration testing of your web layer by simulating the complete `DispatcherServlet` HTTP request-response pipeline in memory—without spinning up a live network server or binding to a real TCP port.

In this lesson, you will master testing REST API endpoints using `@WebMvcTest` slices, performing HTTP assertions with `MockMvc`, validating JSON payloads with `jsonPath()`, and isolating dependencies with `@MockitoBean`.

---

## 1. `MockMvc` Sliced Execution Pipeline

``` mermaid
flowchart TD
    subgraph MockEnvironment["In-Memory MockMvc Test Harness"]
        TestRunner["MockMvc Request (POST /api/v1/orders)"]
    end

    subgraph SpringWebSlice["Spring Boot @WebMvcTest Sliced Context"]
        Filters["Security & MDC Logging Filters"]
        Dispatcher["DispatcherServlet"]
        Validations["@Valid Bean Validation Handler"]
        Controller["OrderRestController"]
        ExceptionAdv["@RestControllerAdvice (ProblemDetails)"]
        
        TestRunner --> Filters --> Dispatcher --> Validations --> Controller
        Controller -.->|Throws Exception| ExceptionAdv
    end

    subgraph MockedCollaborators["Mocked Service Dependencies (@MockitoBean)"]
        OrderServiceMock["OrderService (Mock Proxy)"]
        Controller -->|Calls service| OrderServiceMock
    end

    Controller -->|Returns DTO| Dispatcher -->|Jackson JSON Serialization| TestRunner
```

---

## 2. Fast Web Slicing with `@WebMvcTest`

Instead of loading the entire `ApplicationContext` (which loads Hibernate, Datasources, and Schedulers), use `@WebMvcTest` to load only web infrastructure:

```java
package com.example.ecommerce.order;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.util.List;

import static org.hamcrest.Matchers.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(OrderRestController.class) // Loads ONLY OrderRestController & MVC infrastructure!
class OrderRestControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockitoBean // Injects mock into WebMvcTest application context (Spring Boot 3.4+ / 4.x)
    private OrderService orderService;

    @Test
    @DisplayName("POST /api/v1/orders - Should return 201 Created when payload is valid")
    void shouldCreateOrderSuccessfully() throws Exception {
        // Given
        CreateOrderRequest request = new CreateOrderRequest(
                "CUST-100", 
                List.of(new OrderItemDto("SKU-LAPTOP", 1, new BigDecimal("1200.00")))
        );
        OrderResponse response = new OrderResponse(1L, "CUST-100", new BigDecimal("1200.00"), OrderStatus.COMPLETED);

        when(orderService.createOrder(any())).thenReturn(response);

        // When & Then
        mockMvc.perform(post("/api/v1/orders")
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "/api/v1/orders/1"))
                .andExpect(jsonPath("$.id").value(1))
                .andExpect(jsonPath("$.customerId").value("CUST-100"))
                .andExpect(jsonPath("$.totalAmount").value(1200.00))
                .andExpect(jsonPath("$.status").value("COMPLETED"));
    }
}
```

---

## 3. Testing Bean Validation & Error Handlers

Integration tests must verify that invalid requests are rejected with proper HTTP 400 Bad Request status codes and RFC 7807 `ProblemDetails` payloads:

```java
@Test
@DisplayName("POST /api/v1/orders - Should return 400 Bad Request when customerId is blank")
void shouldRejectInvalidOrderPayload() throws Exception {
    // Given (Invalid Request violating @NotBlank constraint)
    CreateOrderRequest invalidRequest = new CreateOrderRequest(
            "", // Blank customer ID!
            List.of() // Empty item list violating @NotEmpty!
    );

    // When & Then
    mockMvc.perform(post("/api/v1/orders")
            .contentType(MediaType.APPLICATION_JSON)
            .content(objectMapper.writeValueAsString(invalidRequest)))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.title").value("Bad Request"))
            .andExpect(jsonPath("$.status").value(400))
            .andExpect(jsonPath("$.errors", hasSize(2)))
            .andExpect(jsonPath("$.errors[*].field", containsInAnyOrder("customerId", "items")));
}
```

---

## 4. `@WebMvcTest` vs `@SpringBootTest`

| Feature | `@WebMvcTest` (Sliced Test) | `@SpringBootTest` (Full Integration) |
| :--- | :--- | :--- |
| **Startup Speed** | Ultra-Fast (~1–2 seconds). | Slower (~5–15 seconds). |
| **Context Scope** | Loads Controllers, Advice, Converters, Jackson. | Loads the full, entire `ApplicationContext`. |
| **Database & JPA** | NOT loaded (requires `@MockitoBean` for services). | Real or embedded database initialized. |
| **Network Port** | In-memory `MockMvc` (No TCP port bound). | Can bind to `webEnvironment = RANDOM_PORT`. |
| **Primary Use Case** | Testing controller routing, DTO validation, headers, and JSON serialization. | End-to-end user workflows spanning controller, service, and database. |

---

## 5. Spring Boot 3 vs Spring Boot 4: Web Testing Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.0–3.3"]
        MockBeanLegacy["@MockBean (Spring Boot Test package)"]
        MockMvcClassic["Classic MockMvc ResultMatchers"]
        ManualRestClientMock["MockRestServiceServer for RestClient"]
    end

    subgraph SB4["Spring Boot 3.4+ & 4.x"]
        MockitoBeanCore["@MockitoBean (Core Spring Framework 6.2+)"]
        EnhancedProblemDetails["RFC 9457 ProblemDetails 2.0 Assertions"]
        HttpExchangeTesting["Native HTTP Interface @HttpExchange Mock Clients"]
    end

    SB3 ==>|Core @MockitoBean & ProblemDetails 2.0 Integration| SB4
```

### Key Differences & Configuration Comparison

| Web Testing Feature | Spring Boot 3.0–3.3 | Spring Boot 3.4+ & 4.x |
| :--- | :--- | :--- |
| **Bean Mocking** | Used `@MockBean` inside `@WebMvcTest`. | **`@MockitoBean`**: First-class core Spring Framework annotation replacing deprecated `@MockBean`. |
| **Error Specification** | Default RFC 7807 `ProblemDetails` responses. | **RFC 9457 Standard**: Extended error properties automatically tested via `status().isProblemDetail()`. |

---

## 6. Primary Sources & Further Reading

- [Spring Boot Testing Reference Guide](https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.testing) — `@WebMvcTest`, `@SpringBootTest`, and slice testing.
- [Jayway JsonPath Documentation](https://github.com/json-path/JsonPath) — Advanced JSON syntax matching for REST assertions.

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the primary advantage of using `@WebMvcTest` over `@SpringBootTest` when testing REST controllers?"
    **Answer**: `@WebMvcTest` only bootstraps the web layer (Controllers, filters, Jackson, validation) rather than the complete Spring context, executing in ~1 second compared to ~10+ seconds for a full context boot.

??? question "Question 2: Does `MockMvc` open a real network port on your machine during test execution?"
    **Answer**: No; `MockMvc` simulates the full `DispatcherServlet` pipeline entirely in-memory without opening a real TCP socket or HTTP server.

??? question "Question 3: How do you verify that a JSON response contains a specific list size using `jsonPath`?"
    **Answer**: By asserting `.andExpect(jsonPath("$.items", hasSize(expectedCount)))` using Hamcrest matchers.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0049: Mocking with Mockito**](0049-mocking-dependencies-with-mockito.md) | [**All Lessons**](index.md) | [➡️ **0051: Database Testing with Testcontainers**](0051-database-integration-testing-testcontainers.md) |
