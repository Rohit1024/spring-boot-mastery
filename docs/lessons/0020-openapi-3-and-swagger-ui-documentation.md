---
icon: lucide/file-text
---

# 0020: API Documentation with OpenAPI 3, SpringDoc & Swagger UI

In distributed microservice architectures, API contracts are the formal agreement between frontend apps, mobile clients, external partners, and backend services. Manually written documentation inevitably suffers from **documentation drift** — becoming outdated as code evolves.

**OpenAPI 3 (OAS3)** and **SpringDoc** solve this by generating interactive, live documentation directly from compiled Spring `@RestController` metadata and Jakarta Bean Validation constraints.

In this lesson, you will integrate `springdoc-openapi`, annotate endpoints and DTOs with rich metadata, configure **JWT Bearer Authentication** in Swagger UI, and segment endpoints using **Grouped APIs**.

---

## 1. SpringDoc OpenAPI 3 Architecture

SpringDoc inspects Spring MVC's `RequestMappingHandlerMapping`, Java reflection metadata, and Jakarta Bean Validation annotations (`@NotNull`, `@Size`, `@Pattern`) at runtime to dynamically construct an OpenAPI 3.0 specification in JSON/YAML:

``` mermaid
flowchart LR
    subgraph SpringApp["🚀 Spring Boot 3 Application"]
        Controllers["@RestController Endpoints"]
        DTOs["DTO Records + @Schema + @Valid"]
        Config["OpenAPI Configuration Bean"]
        
        SpringDoc["⚡ SpringDoc OpenAPI Engine"]
        
        Controllers --> SpringDoc
        DTOs --> SpringDoc
        Config --> SpringDoc
    end

    Spec["📄 /v3/api-docs<br/>(OpenAPI 3.0 JSON Spec)"]
    SwaggerUI["🖥️ /swagger-ui.html<br/>(Interactive API Playground)"]
    Generator["🛠️ OpenAPI Generator<br/>(TypeScript / Kotlin SDKs)"]

    SpringDoc --> Spec
    Spec --> SwaggerUI
    Spec --> Generator
```

---

## 2. Dependency Setup (Spring Boot 3.x)

Add `springdoc-openapi-starter-webmvc-ui` to your build:

```xml
<dependency>
    <groupId>org.springdoc</groupId>
    <artifactId>springdoc-openapi-starter-webmvc-ui</artifactId>
    <version>2.8.5</version>
</dependency>
```

### Basic Properties (`application.yml`)

```yaml
springdoc:
  api-docs:
    path: /v3/api-docs # Raw OpenAPI JSON specification path
  swagger-ui:
    path: /swagger-ui.html # Interactive UI dashboard
    tags-sorter: alpha
    operations-sorter: method
    doc-expansion: none
```

---

## 3. Global OpenAPI Definition & JWT Security Configuration

To enable the **"Authorize" (Bearer Token)** button in Swagger UI:

```java
package com.example.demo.config;

import io.swagger.v3.oas.annotations.OpenAPIDefinition;
import io.swagger.v3.oas.annotations.enums.SecuritySchemeType;
import io.swagger.v3.oas.annotations.info.Contact;
import io.swagger.v3.oas.annotations.info.Info;
import io.swagger.v3.oas.annotations.info.License;
import io.swagger.v3.oas.annotations.security.SecurityScheme;
import io.swagger.v3.oas.annotations.servers.Server;
import org.springframework.context.annotation.Configuration;

@Configuration
@OpenAPIDefinition(
    info = @Info(
        title = "Enterprise Payment & Order API",
        version = "v1.0.0",
        description = "Production REST API for high-volume transactions, checkout flows, and user management.",
        contact = @Contact(name = "API Support", email = "api-support@example.com"),
        license = @License(name = "Apache 2.0", url = "https://www.apache.org/licenses/LICENSE-2.0")
    ),
    servers = {
        @Server(url = "http://localhost:8080", description = "Local Development Server"),
        @Server(url = "https://api.staging.example.com", description = "Staging Cluster")
    }
)
@SecurityScheme(
    name = "BearerAuth",
    type = SecuritySchemeType.HTTP,
    scheme = "bearer",
    bearerFormat = "JWT",
    description = "Enter JWT Bearer token to authorize requests across protected endpoints."
)
public class OpenApiConfig {
}
```

---

## 4. Annotating DTOs with `@Schema`

`@Schema` decorates request and response payloads with field descriptions, validation ranges, default values, and realistic examples:

```java
package com.example.demo.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;

import java.math.BigDecimal;

@Schema(description = "Request payload for creating a new customer purchase order")
public record CreateOrderRequest(

    @Schema(description = "Unique identifier of the customer", example = "usr_9482910")
    @NotBlank(message = "Customer ID is required")
    String customerId,

    @Schema(description = "SKU product code to purchase", example = "PROD-MACBOOK-M3")
    @NotBlank(message = "Product code is required")
    String productCode,

    @Schema(description = "Quantity of items to purchase", example = "2", minimum = "1", maximum = "100")
    @NotNull @Positive
    Integer quantity,

    @Schema(description = "Unit price of the item", example = "1999.99")
    @NotNull @Positive
    BigDecimal unitPrice
) {}
```

---

## 5. Annotating `@RestController` Endpoints

Decorate controller methods with `@Operation`, `@ApiResponses`, and `@Parameter`:

```java
package com.example.demo.controller;

import com.example.demo.dto.CreateOrderRequest;
import com.example.demo.dto.OrderResponse;
import com.example.demo.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.net.URI;

@RestController
@RequestMapping("/api/v1/orders")
@RequiredArgsConstructor
@Tag(name = "Orders API", description = "Operations for creating, retrieving, and canceling customer orders")
@SecurityRequirement(name = "BearerAuth") // Enforces Bearer token in Swagger UI
public class OrderController {

    private final OrderService orderService;

    @Operation(
        summary = "Create a new order",
        description = "Validates inventory, reserves stock, and places a new customer purchase order."
    )
    @ApiResponses({
        @ApiResponse(
            responseCode = "201",
            description = "Order placed successfully",
            content = @Content(schema = @Schema(implementation = OrderResponse.class))
        ),
        @ApiResponse(
            responseCode = "400",
            description = "Invalid order input payload or validation failure",
            content = @Content(schema = @Schema(implementation = ProblemDetail.class))
        ),
        @ApiResponse(
            responseCode = "401",
            description = "Unauthorized - Missing or invalid Bearer JWT",
            content = @Content(schema = @Schema(implementation = ProblemDetail.class))
        )
    })
    @PostMapping
    public ResponseEntity<OrderResponse> createOrder(@Valid @RequestBody CreateOrderRequest request) {
        OrderResponse response = orderService.createOrder(request);
        return ResponseEntity
                .created(URI.create("/api/v1/orders/" + response.id()))
                .body(response);
    }

    @Operation(summary = "Retrieve order by ID", description = "Fetches complete order details by its unique identifier.")
    @GetMapping("/{id}")
    public ResponseEntity<OrderResponse> getOrderById(
            @Parameter(description = "Primary key ID of the order", example = "42")
            @PathVariable Long id) {
        return ResponseEntity.ok(orderService.getOrderById(id));
    }
}
```

---

## 6. Segmenting Documentation with Grouped APIs

In enterprise systems, internal administrative endpoints should be separated from public customer endpoints. SpringDoc supports **Grouped APIs**:

```java
package com.example.demo.config;

import org.springdoc.core.models.GroupedOpenApi;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ApiGroupingConfig {

    @Bean
    public GroupedOpenApi publicApi() {
        return GroupedOpenApi.builder()
                .group("1-public-api")
                .pathsToMatch("/api/v1/orders/**", "/api/v1/products/**")
                .build();
    }

    @Bean
    public GroupedOpenApi adminApi() {
        return GroupedOpenApi.builder()
                .group("2-admin-api")
                .pathsToMatch("/api/v1/admin/**", "/actuator/**")
                .build();
    }
}
```
*In Swagger UI, a dropdown appears in the top-right corner, allowing users to switch between the Public API and Admin API specifications.*

---

## 7. Primary Sources & Further Reading

- [SpringDoc Official Documentation](https://springdoc.org/) — Authoritative guide for Spring Boot 3.x integration and configuration.
- [OpenAPI Specification v3.1.0](https://spec.openapis.org/oas/v3.1.0) — The official OpenAPI standard.
- [Swagger UI Configuration Options](https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration/) — Customizing layout and theme.

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: How does SpringDoc dynamically populate field validation constraints in Swagger UI?"
    **Answer**: SpringDoc automatically reflects on Jakarta Bean Validation annotations (`@NotNull`, `@Size`, `@Positive`) on DTO fields and translates them directly into OpenAPI schema constraints.

??? question "Question 2: What is the purpose of `@SecurityScheme` and `@SecurityRequirement` in SpringDoc?"
    **Answer**: `@SecurityScheme` defines the authentication mechanism (e.g. JWT Bearer token), and `@SecurityRequirement` attaches that scheme to specific controllers to enable authorized testing in Swagger UI.

??? question "Question 3: How does `GroupedOpenApi` improve documentation in large microservices?"
    **Answer**: It segments large API catalogs into focused sub-specifications (such as Public vs Admin endpoints) selectable via a dropdown in Swagger UI.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0019: Production Health & Actuator Metrics**](0019-production-health-actuator-and-metrics.md) | [**All Lessons**](index.md) | [➡️ **0021: Structured Logging & MDC**](0021-structured-logging-logback-mdc.md) |
