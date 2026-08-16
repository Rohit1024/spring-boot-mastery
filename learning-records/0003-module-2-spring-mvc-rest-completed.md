# Module 2: RESTful Web Services & Spring MVC Completed

Completed Module 2 mastering the web layer and RESTful API architecture in Spring Boot 3.x.

## Key Competencies Acquired
- **DispatcherServlet & Web MVC Pipeline**: Understood the Front Controller pattern, `HandlerMapping`, `HandlerAdapter`, `HandlerInterceptor` lifecycle (`preHandle`, `postHandle`, `afterCompletion`), and how `HttpMessageConverter` (Jackson) serializes/deserializes HTTP payloads.
- **RESTful CRUD Design & Semantics**: Built controllers with `@RestController`, `@PathVariable`, `@RequestParam`, `@RequestBody`, and `ResponseEntity<T>`, returning proper HTTP status codes (`200 OK`, `201 Created` with `Location` header, `204 No Content`, `400 Bad Request`, `404 Not Found`). Understood HTTP safety and idempotency rules (PUT vs PATCH).
- **Jakarta Bean Validation**: Implemented input validation using `@Valid`, `@Validated`, constraint annotations (`@NotBlank`, `@Min`, `@Pattern`), validation groups (`OnCreate` vs `OnUpdate`), nested object graph validation, and custom `ConstraintValidator` implementations.
- **Global Exception Handling with ProblemDetail**: Centralized error interception via `@RestControllerAdvice` extending `ResponseEntityExceptionHandler`, implementing standard RFC 9457 / RFC 7807 `ProblemDetail` schemas to prevent information leakage while enhancing client diagnostics.
- **DTOs & Response Envelopes**: Established boundary decoupling between JPA database entities and API contracts using Java 17+ `record` classes, standardized `ApiResponse<T>` envelopes, and high-performance compile-time code generation with MapStruct.
- **Enterprise Design Patterns**: Leveraged Spring IoC to implement the Strategy Pattern (automatic `Map<String, StrategyInterface>` injection for dynamic payment routing) and the Decorator Pattern with `@Primary` and delegation.
