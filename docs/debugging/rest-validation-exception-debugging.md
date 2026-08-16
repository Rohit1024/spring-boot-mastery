---
icon: lucide/bug
---

# Troubleshooting REST API Exceptions: Validation, Deserialization & Media Types

When developing and operating RESTful services in Spring Boot, API consumers frequently encounter client-side (`4xx`) and unexpected server-side (`500`) failures.

This diagnostic playbook covers root-cause analyses, sequence traces, and concrete resolutions for the 4 most common REST API exceptions in Spring Boot 3.x.

---

## 1. Quick Diagnostic Decision Tree

``` mermaid
flowchart TD
    Start["🚨 API Request Failed"] --> CheckStatus{"What is the HTTP Status Code?"}
    
    CheckStatus -->|400 Bad Request| Check400{"Inspect Error Payload"}
    Check400 -->|MethodArgumentNotValidException| FixVal["Fix: Field failed @Valid constraint.<br/>Inspect invalidFields map in ProblemDetail."]
    Check400 -->|HttpMessageNotReadableException| FixJSON["Fix: Malformed JSON syntax or type mismatch<br/>(e.g., passing 'abc' into Integer field)."]
    
    CheckStatus -->|415 Unsupported Media Type| Fix415["Fix: Client omitted or set wrong Content-Type.<br/>Must send 'Content-Type: application/json'."]
    
    CheckStatus -->|405 Method Not Allowed| Fix405["Fix: Verb mismatch (e.g. sending POST to @GetMapping).<br/>Check Allow header in response."]
    
    CheckStatus -->|CORS Preflight Failed| FixCORS["Fix: Missing @CrossOrigin or WebMvcConfigurer<br/>CorsRegistry configuration."]
```

---

## 2. Issue 1: `MethodArgumentNotValidException` (Validation Failures)

### The Symptom:
Client receives `400 Bad Request`, but the response is either a generic message or contains an unparsed raw Java exception string.

### The Root Cause:
A request body failed one or more Jakarta Bean Validation constraints (`@NotBlank`, `@Min`, `@Pattern`) triggered by `@Valid`.

``` mermaid
sequenceDiagram
    autonumber
    Client->>DispatcherServlet: POST /api/v1/users {"age": 12}
    DispatcherServlet->>RequestMappingHandlerAdapter: Invoke handle()
    RequestMappingHandlerAdapter->>HibernateValidator: Validate UserRequest DTO
    HibernateValidator-->>RequestMappingHandlerAdapter: Violation: age < 18 (@Min)
    RequestMappingHandlerAdapter-->>DispatcherServlet: Throw MethodArgumentNotValidException
    DispatcherServlet->>GlobalExceptionHandler: Intercept with @RestControllerAdvice
    GlobalExceptionHandler-->>Client: 400 Bad Request (RFC 9457 with invalidFields)
```

### The Resolution:
Capture `BindingResult.getFieldErrors()` in your global `@RestControllerAdvice` and format it into a structured map:

```java
@Override
protected ResponseEntity<Object> handleMethodArgumentNotValid(
        MethodArgumentNotValidException ex,
        HttpHeaders headers,
        HttpStatusCode status,
        WebRequest request) {

    ProblemDetail problemDetail = ProblemDetail.forStatusAndDetail(
            HttpStatus.BAD_REQUEST, "Validation failed for one or more fields");

    Map<String, String> fieldErrors = new HashMap<>();
    for (FieldError error : ex.getBindingResult().getFieldErrors()) {
        fieldErrors.put(error.getField(), error.getDefaultMessage());
    }
    problemDetail.setProperty("invalidFields", fieldErrors);

    return new ResponseEntity<>(problemDetail, HttpStatus.BAD_REQUEST);
}
```

---

## 3. Issue 2: `HttpMessageNotReadableException` (JSON Deserialization Mismatch)

### The Symptom:
Client receives `400 Bad Request` with:
`JSON parse error: Cannot deserialize value of type java.lang.Integer from String "premium"`

### The Root Cause:
1. Client passed a String where an Integer, Long, or Boolean was expected.
2. An invalid Enum string was passed that does not match any constant in the target Java `enum`.
3. Malformed JSON syntax (trailing comma, unquoted key, unclosed brace).

### The Resolution:
1. Use Jackson `@JsonFormat` or custom deserializers for complex formats:
```java
public record SubscriptionRequest(
    @NotNull
    PlanType planType, // Enum: FREE, PRO, ENTERPRISE

    @JsonFormat(pattern = "yyyy-MM-dd")
    LocalDate startDate
) {}
```
2. Enable case-insensitive enum parsing in Jackson via `application.yml`:
```yaml
spring:
  jackson:
    deserialization:
      read-unknown-enum-values-as-null: false
      accept-empty-string-as-null-object: true
```

---

## 4. Issue 3: `HttpMediaTypeNotSupportedException` (415)

### The Symptom:
Client sends `POST /api/v1/orders` with a valid JSON body, but gets:
`HTTP 415 Unsupported Media Type: Content-Type 'text/plain;charset=UTF-8' is not supported`

### The Root Cause:
The HTTP client (e.g. Curl, Axios, Postman) omitted the `Content-Type: application/json` header, causing Tomcat to default to `text/plain` or `application/x-www-form-urlencoded`.

### The Resolution:
1. **Client Fix**: Explicitly pass header `Content-Type: application/json`.
2. **Controller Safeguard**: Specify `consumes` and `produces` headers on `@PostMapping`:
```java
@PostMapping(
    consumes = MediaType.APPLICATION_JSON_VALUE,
    produces = MediaType.APPLICATION_JSON_VALUE
)
public ResponseEntity<OrderResponse> createOrder(@Valid @RequestBody CreateOrderRequest req) {
    ...
}
```

---

## 5. Issue 4: Cross-Origin Resource Sharing (CORS) Failures

### The Symptom:
Browser console displays:
`Access to XMLHttpRequest at 'http://localhost:8080/api/v1/data' from origin 'http://localhost:3000' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.`

``` mermaid
sequenceDiagram
    autonumber
    Browser->>Backend: HTTP OPTIONS /api/v1/data (Preflight)
    Note over Browser,Backend: Origin: http://localhost:3000<br/>Access-Control-Request-Method: POST
    Backend-->>Browser: HTTP 403 Forbidden (Missing CORS headers)
    Note over Browser: Browser blocks actual POST request!
```

### The Resolution:
Configure a global `CorsConfigurationSource` or register via `WebMvcConfigurer`:

```java
@Configuration
public class CorsConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins("http://localhost:3000", "https://app.example.com")
                .allowedMethods("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600); // Cache preflight response for 1 hour
    }
}
```

---

## 🧭 Navigation & Diagnostic Playbooks

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Circular Dependencies & BeanCreationException**](circular-dependencies.md) | [**All Debugging Guides**](index.md) | [➡️ **Hibernate N+1 & LazyInitializationException**](jpa-n-plus-one-and-lazy-init.md) |

