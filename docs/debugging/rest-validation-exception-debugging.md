---
icon: lucide/bug
---

# Troubleshooting REST API exceptions: Validation, deserialization, and media types

When developing and operating RESTful services in Spring Boot, API consumers encounter client-side (`4xx`) and server-side (`500`) failures.

Here are the root causes, sequence traces, and resolutions for the 4 most common REST API exceptions in Spring Boot 3.x.

---

## 1. Quick diagnostic decision tree

``` mermaid
flowchart TD
    Start["API Request Failed"] --> CheckStatus{"What is the HTTP Status Code?"}
    
    CheckStatus -->|400 Bad Request| Check400{"Inspect Error Payload"}
    Check400 -->|MethodArgumentNotValidException| FixVal["Fix: Field failed @Valid constraint.<br/>Inspect invalidFields map in ProblemDetail."]
    Check400 -->|HttpMessageNotReadableException| FixJSON["Fix: Malformed JSON syntax or type mismatch<br/>(e.g., passing 'abc' into Integer field)."]
    
    CheckStatus -->|415 Unsupported Media Type| Fix415["Fix: Client omitted or set wrong Content-Type.<br/>Must send 'Content-Type: application/json'."]
    
    CheckStatus -->|405 Method Not Allowed| Fix405["Fix: Verb mismatch (e.g. sending POST to @GetMapping).<br/>Check Allow header in response."]
    
    CheckStatus -->|CORS Preflight Failed| FixCORS["Fix: Missing @CrossOrigin or WebMvcConfigurer<br/>CorsRegistry configuration."]
```

---

## 2. Issue 1: `MethodArgumentNotValidException` (Validation failures)

### Symptoms
Client receives `400 Bad Request`, but the response is either a generic message or contains an unparsed raw Java exception string.

### Root cause
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

### Resolution
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

## 3. Issue 2: `HttpMessageNotReadableException` (JSON deserialization mismatch)

### Symptoms
Client receives `400 Bad Request` with:
`JSON parse error: Cannot deserialize value of type java.lang.Integer from String "premium"`

### Root cause
1. Client passed a string where an integer, long, or boolean was expected.
2. An invalid enum string was passed that does not match any constant in the target Java `enum`.
3. Malformed JSON syntax (trailing comma, unquoted key, unclosed brace).

### Resolution
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

### Symptoms
Client sends `POST /api/v1/orders` with a valid JSON body, but gets:
`HTTP 415 Unsupported Media Type: Content-Type 'text/plain;charset=UTF-8' is not supported`

### Root cause
The HTTP client omitted the `Content-Type: application/json` header, causing Tomcat to default to `text/plain` or `application/x-www-form-urlencoded`.

### Resolution
1. **Client fix**: Explicitly pass header `Content-Type: application/json`.
2. **Controller safeguard**: Specify `consumes` and `produces` headers on `@PostMapping`:
```java
@PostMapping(
    consumes = MediaType.APPLICATION_JSON_VALUE,
    produces = MediaType.APPLICATION_JSON_VALUE
)
public ResponseEntity<OrderResponse> createOrder(@Valid @RequestBody CreateOrderRequest req) {
    // Controller logic
}
```

---

## 5. Issue 4: Cross-Origin Resource Sharing (CORS) failures

### Symptoms
Browser console displays:
`Access to XMLHttpRequest at 'http://localhost:8080/api/v1/data' from origin 'http://localhost:3000' has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.`

``` mermaid
sequenceDiagram
    autonumber
    Browser->>Backend: HTTP OPTIONS /api/v1/data (Preflight)
    Note over Browser,Backend: Origin: http://localhost:3000<br/>Access-Control-Request-Method: POST
    Backend-->>Browser: HTTP 403 Forbidden (Missing CORS headers)
    Note over Browser: Browser blocks actual POST request.
```

### Resolution
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

## Navigation and debugging index

| Previous | Debugging index | Next |
| :--- | :---: | ---: |
| [**Circular dependencies and BeanCreationException**](circular-dependencies.md) | [**All debugging guides**](index.md) | [**Hibernate N+1 and LazyInitializationException**](jpa-n-plus-one-and-lazy-init.md) |
