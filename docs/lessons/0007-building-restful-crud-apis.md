---
icon: lucide/server
---

# 0007: Building RESTful CRUD APIs with controllers, RequestMapping, and HTTP status codes

REST (Representational State Transfer) is the foundation of modern web and microservice communication. 

In this lesson, we master **Spring MVC REST controllers**, request parameter binding, HTTP method semantics, **safe vs idempotent operations**, and how to return precise **HTTP status codes and headers** using `ResponseEntity<T>`.

---

## 1. REST architectural foundations

A RESTful API organizes operations around **Resources** identified by standardized URI paths (nouns, plural, hierarchical), acted upon using standard **HTTP Verbs**:

``` mermaid
flowchart TD
    Client["📱 Client Application"] 
    
    subgraph REST_Operations["HTTP Verbs on Resource: /api/v1/products"]
        POST["POST /products<br/><i>(Create new resource)</i>"]
        GET["GET /products/{id}<br/><i>(Retrieve resource)</i>"]
        PUT["PUT /products/{id}<br/><i>(Replace resource)</i>"]
        PATCH["PATCH /products/{id}<br/><i>(Partial update)</i>"]
        DELETE["DELETE /products/{id}<br/><i>(Delete resource)</i>"]
    end
    
    Client --> POST
    Client --> GET
    Client --> PUT
    Client --> PATCH
    Client --> DELETE
```

---

## 2. Http method semantics: Safety idempotency

Understanding **Safety** and **Idempotency** is critical for building resilient distributed systems and handling network retries:

``` mermaid
stateDiagram-v2
    [*] --> ResourceExists : POST /products (201 Created)
    ResourceExists --> ResourceExists : GET /products/1 (200 OK - Safe & Idempotent)
    ResourceExists --> ResourceModified : PUT /products/1 (200 OK - Idempotent Replacement)
    ResourceModified --> ResourcePatched : PATCH /products/1 (200 OK - Partial Update)
    ResourcePatched --> ResourceDeleted : DELETE /products/1 (204 No Content - Idempotent)
    ResourceDeleted --> [*]
```

| HTTP Method | Safe? (No State Change) | Idempotent? ($f(x) = f(f(x))$) | Typical Status Code | Purpose & Semantics |
| :--- | :---: | :---: | :--- | :--- |
| **`GET`** | ✅ Yes | ✅ Yes | `200 OK` | Reads resource state without side effects. |
| **`POST`** | ❌ No | ❌ No | `201 Created` | Creates a new subordinate resource. Each call creates another resource. |
| **`PUT`** | ❌ No | ✅ Yes | `200 OK` / `204 No Content` | **Full replacement** of the resource at the URI. Calling 5 times results in the exact same state. |
| **`PATCH`** | ❌ No | ⚠️ Contextual | `200 OK` | **Partial update** of specific fields. |
| **`DELETE`** | ❌ No | ✅ Yes | `204 No Content` / `200 OK` | Removes the target resource. Subsequent calls still leave the resource deleted. |

!!! important "PUT vs PATCH"
    - **`PUT`** replaces the entire resource. Missing fields in a `PUT` payload should be reset to default/null.
    - **`PATCH`** modifies only the supplied fields, leaving other fields intact.

---

## 3. Spring mvc controller annotations

Spring makes REST endpoint definition declarative:

``` mermaid
flowchart TD
    Controller["@RestController<br/><i>(@Controller + @ResponseBody)</i>"]
    
    Controller --> Bind1["@PathVariable<br/><i>Extracts from URI path /products/{id}</i>"]
    Controller --> Bind2["@RequestParam<br/><i>Extracts query params /products?page=1&size=20</i>"]
    Controller --> Bind3["@RequestBody<br/><i>Deserializes JSON body into Java DTO</i>"]
    Controller --> Bind4["@RequestHeader<br/><i>Extracts HTTP headers (Authorization, X-Tenant-Id)</i>"]
```

### `@RestController` vs `@Controller`
- `@Controller`: Designed for traditional server-side rendering (Spring MVC + Thymeleaf / JSP). Returns a view template name (e.g., `"index.html"`).
- `@RestController`: Specialized for REST APIs. Combines `@Controller` and `@ResponseBody`, instructing Spring to write return objects directly into the HTTP response body as JSON via Jackson `HttpMessageConverter`.

---

## 4. Production-ready REST CRUD controller

Here is an enterprise-grade implementation of a `ProductController` showing clean parameter binding, pagination, `ResponseEntity<T>`, and `Location` URI headers:

### Data transfer objects (dtos)
```java
package com.example.demo.dto;

import java.math.BigDecimal;

public record CreateProductRequest(String name, String description, BigDecimal price, Integer stockQuantity) {}
public record UpdateProductRequest(String name, String description, BigDecimal price, Integer stockQuantity) {}
public record ProductResponse(Long id, String sku, String name, String description, BigDecimal price, Integer stockQuantity) {}
```

### The REST controller
```java
package com.example.demo.controller;

import com.example.demo.dto.CreateProductRequest;
import com.example.demo.dto.ProductResponse;
import com.example.demo.dto.UpdateProductRequest;
import com.example.demo.service.ProductService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

import java.net.URI;

@RestController
@RequestMapping("/api/v1/products")
@RequiredArgsConstructor
public class ProductController {

    private final ProductService productService;

    // 1. CREATE (POST) -> Returns 201 Created with Location Header
    @PostMapping
    public ResponseEntity<ProductResponse> createProduct(@RequestBody CreateProductRequest request) {
        ProductResponse createdProduct = productService.createProduct(request);

        // Build canonical URI: /api/v1/products/{id}
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{id}")
                .buildAndExpand(createdProduct.id())
                .toUri();

        return ResponseEntity.created(location).body(createdProduct);
    }

    // 2. READ SINGLE (GET) -> Returns 200 OK
    @GetMapping("/{id}")
    public ResponseEntity<ProductResponse> getProductById(@PathVariable Long id) {
        ProductResponse product = productService.getProductById(id);
        return ResponseEntity.ok(product);
    }

    // 3. READ PAGINATED & FILTERED (GET) -> Returns 200 OK
    @GetMapping
    public ResponseEntity<Page<ProductResponse>> listProducts(
            @RequestParam(required = false) String search,
            @PageableDefault(size = 20, sort = "name") Pageable pageable) {
        Page<ProductResponse> products = productService.listProducts(search, pageable);
        return ResponseEntity.ok(products);
    }

    // 4. FULL UPDATE (PUT) -> Returns 200 OK
    @PutMapping("/{id}")
    public ResponseEntity<ProductResponse> updateProduct(
            @PathVariable Long id,
            @RequestBody UpdateProductRequest request) {
        ProductResponse updated = productService.updateProduct(id, request);
        return ResponseEntity.ok(updated);
    }

    // 5. DELETE (DELETE) -> Returns 204 No Content
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteProduct(@PathVariable Long id) {
        productService.deleteProduct(id);
        return ResponseEntity.noContent().build();
    }
}
```

---

## 5. Best practices for enterprise REST APIs

1. **Plural Nouns for Resources**: Use `/api/v1/users`, `/api/v1/orders` (never `/api/v1/getUser` or `/api/v1/deleteOrder`).
2. **Explicit API Versioning**: Include the major version in the URI path (`/api/v1/...`) to prevent breaking external clients during contract changes.
3. **Use the `Location` Header on 201 Created**: When a resource is created via `POST`, always return the `Location` header pointing to the newly minted resource URI.
4. **Return `204 No Content` for Void Deletions**: Do not return empty JSON `{}` or string `"OK"`; `204 No Content` communicates completion with zero body payload.

---

## 6. Spring Boot 3 vs Spring Boot 4: REST API client evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        RestTemplate["RestTemplate (Maintenance Mode)"]
        ManualClients["Manual WebClient / RestClient Setup"]
        ClassDTOs["Class-Based DTO Envelopes"]
    end

    subgraph SB4["Spring Boot 4.x"]
        DeclarativeHTTP["Declarative @HttpExchange Interfaces"]
        AutoRestClient["Auto-Configured RestClient Builders"]
        RecordFirst["Record-First DTO Serialization"]
    end

    SB3 ==>|Client Modernization| SB4
```

### Key differences and configuration comparison

| REST API Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Synchronous HTTP Client** | `RestTemplate` (legacy) / `RestClient` (introduced in 3.2). | **`RestClient` as the Official Standard**: `RestTemplate` deprecated for new architectures. |
| **Declarative Clients** | Required Spring Cloud OpenFeign or manual `HttpServiceProxyFactory`. | **Native Declarative `@HttpExchange` Starters**: Direct interface proxies generated out-of-the-box. |
| **Payload Representation** | Standard classes with Jackson ObjectMapper. | **Java Record Payloads**: Zero-reflection Jackson 3 / Jakarta JSON Binding serialization. |

```java
// Spring Boot 4 Declarative HTTP Client Interface
package com.example.client;

import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.service.annotation.GetExchange;
import org.springframework.web.service.annotation.HttpExchange;

@HttpExchange("/api/v1/users")
public interface UserClient {

    @GetExchange("/{id}")
    UserResponse getUserById(@PathVariable("id") Long id);

    @GetExchange
    List<UserResponse> listUsers(@RequestParam("role") String role);
}
```

---

## 7. Primary sources and further reading

- [Spring Framework Reference: REST Controllers](https://docs.spring.io/spring-framework/reference/web/webmvc/mvc-controller.html), Controller mappings, parameters, and return types.
- [RESTful Web Services Architectural Principles (Roy Fielding)](https://www.ics.uci.edu/~fielding/pubs/dissertation/rest_arch_style.htm), The original dissertation defining REST constraints.
- [MDN Web Docs: HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status), Comprehensive HTTP status code specifications.

---

## 8. Knowledge check and practice

??? question "Question 1: What is the semantic difference between the `@Controller` and `@RestController` annotations?"
    **Answer**: `@RestController` combines `@Controller` and `@ResponseBody`, ensuring all method return values are automatically serialized into the HTTP response body as JSON.

??? question "Question 2: Why is `PUT` classified as an idempotent operation while `POST` is not?"
    **Answer**: Executing `PUT` multiple times with identical data results in the exact same resource state, whereas repeated `POST` requests create multiple distinct resources.

??? question "Question 3: Which HTTP status code should be returned when a `DELETE` endpoint successfully removes a resource with no body content returned?"
    **Answer**: Return `204 No Content` to signal successful execution without sending an unnecessary payload.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0006: Servlet Architecture vs DispatcherServlet**](0006-servlet-architecture-and-dispatcherservlet.md) | [**All Lessons**](index.md) | [ **0008: Spring Bean Validation**](0008-spring-bean-validation.md) |

