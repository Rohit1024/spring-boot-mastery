---
icon: lucide/file-code
---

# Spring Web MVC and REST APIs cheatsheet

Reference guide for annotations, parameter binding, HTTP status codes, Jakarta Bean Validation, and MapStruct mapping in Spring Boot 3.x.

---

## 1. Core Spring REST annotations

```java
@RestController
@RequestMapping("/api/v1/resources")
public class ResourceController {

    // 1. GET with path variable
    @GetMapping("/{id}")
    public ResponseEntity<ResourceResponse> getById(@PathVariable Long id) { ... }

    // 2. GET with query parameters and pagination
    @GetMapping
    public ResponseEntity<Page<ResourceResponse>> list(
            @RequestParam(defaultValue = "") String filter,
            @PageableDefault(size = 20) Pageable pageable) { ... }

    // 3. POST with request body and validation
    @PostMapping
    public ResponseEntity<ResourceResponse> create(@Valid @RequestBody CreateRequest dto) {
        URI location = ServletUriComponentsBuilder.fromCurrentRequest()
                .path("/{id}").buildAndExpand(saved.id()).toUri();
        return ResponseEntity.created(location).body(saved);
    }

    // 4. PUT (Full replacement)
    @PutMapping("/{id}")
    public ResponseEntity<ResourceResponse> replace(
            @PathVariable Long id, 
            @Valid @RequestBody UpdateRequest dto) { ... }

    // 5. DELETE
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable Long id) {
        return ResponseEntity.noContent().build();
    }
}
```

---

## 2. HTTP status codes reference table

| Status code | Meaning | When to use |
| :--- | :--- | :--- |
| `200 OK` | Success | Standard response for successful `GET`, `PUT`, `PATCH`. |
| `201 Created` | Created | Successful `POST`. Always include `Location` header URI. |
| `204 No Content` | No Content | Successful `DELETE` or update operations returning no body. |
| `400 Bad Request` | Bad Request | Validation failures, malformed JSON, or missing mandatory headers. |
| `401 Unauthorized` | Unauthenticated | Missing or invalid authentication token. |
| `403 Forbidden` | Unauthorized | Authenticated user lacks required permissions or role. |
| `404 Not Found` | Not Found | Target resource does not exist at requested URI. |
| `409 Conflict` | Conflict | Duplicate unique key or business constraint violation. |
| `415 Unsupported Media Type` | Unsupported Media | Client sent unsupported `Content-Type`. |
| `500 Internal Server Error` | Server Error | Uncaught server-side exception. Never expose stack traces to clients. |

---

## 3. Jakarta Bean Validation annotations

```java
public record UserRequest(
    @NotBlank(message = "Username cannot be blank")
    @Size(min = 3, max = 50)
    String username,

    @NotBlank
    @Email(message = "Must be a valid email")
    String email,

    @Min(value = 18, message = "Must be at least 18 years old")
    @Max(120)
    int age,

    @NotNull
    @Positive
    BigDecimal salary,

    @Past
    LocalDate dateOfBirth,

    @NotNull
    @Valid // Cascades validation to nested DTO
    AddressDto address
) {}
```

---

## 4. ProblemDetail (RFC 9457) error response template

```java
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(ResourceNotFoundException.class)
    public ProblemDetail handleNotFound(ResourceNotFoundException ex, HttpServletRequest req) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, ex.getMessage());
        pd.setTitle("Resource Not Found");
        pd.setType(URI.create("https://api.example.com/errors/not-found"));
        pd.setInstance(URI.create(req.getRequestURI()));
        pd.setProperty("timestamp", Instant.now());
        return pd;
    }
}
```

---

## 5. MapStruct mapper pattern

```java
@Mapper(componentModel = MappingConstants.ComponentModel.SPRING)
public interface OrderMapper {
    OrderResponse toResponse(OrderEntity entity);

    @Mapping(target = "id", ignore = true)
    @Mapping(target = "status", constant = "PENDING")
    OrderEntity toEntity(CreateOrderRequest request);
}
```

---

## Navigation and cheatsheet index

| Previous | Cheatsheet index | Next |
| :--- | :---: | ---: |
| [**Spring Core and annotations cheatsheet**](spring-core-annotations.md) | [**All cheatsheets**](index.md) | [**Spring Data JPA and Hibernate cheatsheet**](spring-data-jpa-hibernate.md) |
