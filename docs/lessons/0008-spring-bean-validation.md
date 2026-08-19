---
icon: lucide/shield-check
---

# 0008: Spring bean validation (@Valid, custom validators, and constraint annotations)

Never trust incoming user input. Enterprise applications must sanitize and validate request payloads at the HTTP entry boundary before triggering expensive database queries or business operations.

In this lesson, we master **Jakarta Bean Validation (Hibernate Validator)** in Spring Boot 3.x, standard constraint annotations, validation groups with **`@Validated`**, nested object graph validation, and authoring **custom constraint validators**.

---

## 1. The validation pipeline in Spring mvc

When a client sends a JSON payload to an endpoint annotated with `@Valid` or `@Validated`, Spring MVC coordinates with the Jakarta Validation engine before invoking your controller method:

``` mermaid
sequenceDiagram
    autonumber
    actor Client as 🌐 Client
    participant DS as ⚡ DispatcherServlet
    participant HA as ⚙️ HandlerAdapter
    participant Validator as 🛡️ Hibernate Validator Engine
    participant Ctrl as 🎮 @RestController
    participant ExAdvice as ⚠️ @RestControllerAdvice

    Client->>DS: POST /api/v1/users (JSON body)
    DS->>HA: Dispatch request
    HA->>Validator: Validate UserDTO against @NotBlank, @Min, @Email
    
    alt Validation FAILS (Constraints Violated)
        Validator-->>HA: Constraint Violations detected
        HA-->>DS: Throw MethodArgumentNotValidException
        DS->>ExAdvice: Resolve with @ExceptionHandler
        ExAdvice-->>Client: HTTP 400 Bad Request (RFC 9457 JSON Problem Detail)
    else Validation SUCCEEDS
        Validator-->>HA: Payload valid
        HA->>Ctrl: invoke registerUser(UserDTO)
        Ctrl-->>Client: HTTP 201 Created
    end
```

---

## 2. Standard Jakarta constraint annotations

Adding `spring-boot-starter-validation` brings in the Hibernate Validator reference implementation:

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-validation</artifactId>
</dependency>
```

| Annotation | Applicable Types | Semantics & Validation Rule |
| :--- | :--- | :--- |
| **`@NotNull`** | Any Object | Target cannot be `null` (empty string `""` or whitespace `" "` is permitted). |
| **`@NotEmpty`** | `String`, `Collection`, `Map`, Array | Cannot be `null` and length / size must be `> 0`. |
| **`@NotBlank`** | `String` | Cannot be `null` and trimmed length must be `> 0` (no whitespace-only strings). |
| **`@Size(min, max)`** | `String`, `Collection`, `Map`, Array | Size/length must be within specified bounds. |
| **`@Min(val)` / `@Max(val)`** | `long`, `int`, `BigDecimal`, `BigInteger` | Number must be $\ge \text{min}$ or $\le \text{max}$. |
| **`@Positive` / `@PositiveOrZero`** | Numeric types | Number must be strictly $> 0$ or $\ge 0$. |
| **`@Email`** | `String` | Must match valid RFC 5322 email syntax. |
| **`@Pattern(regexp = "...")`** | `String` | Must match the supplied Regular Expression. |
| **`@Past` / `@Future`** | `LocalDate`, `Instant`, `LocalDateTime` | Date must be strictly before or after current time. |

---

## 3. `@Valid` vs `@Validated` validation groups

``` mermaid
flowchart TD
    subgraph Jakarta["Jakarta Standard (@Valid)"]
        V1["Standard Bean Validation"]
        V2["Cascades to Nested Objects"]
        V3["No support for Validation Groups"]
    end

    subgraph Spring["Spring Extension (@Validated)"]
        S1["Class-level on @RestController / @Service"]
        S2["Enables validation on @PathVariable & @RequestParam"]
        S3["Supports Validation Groups (Create vs Update)"]
    end

    Jakarta ~~~ Spring
```

### Using validation groups (create vs update scenarios)

Often, a field like `id` must be `null` on resource creation, but mandatory on updates:

```java
package com.example.demo.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Null;

public class UserDto {

    // Marker interfaces for groups
    public interface OnCreate {}
    public interface OnUpdate {}

    @Null(groups = OnCreate.class, message = "ID must be null when creating a new user")
    @NotNull(groups = OnUpdate.class, message = "ID is required when updating an existing user")
    private Long id;

    @NotBlank(groups = {OnCreate.class, OnUpdate.class}, message = "Username cannot be blank")
    private String username;

    @NotBlank(groups = OnCreate.class, message = "Password is required for initial registration")
    private String password;
}
```

### In controller
```java
@PostMapping
public ResponseEntity<Void> create(@Validated(UserDto.OnCreate.class) @RequestBody UserDto dto) {
    // Validates only OnCreate constraints
    return ResponseEntity.status(HttpStatus.CREATED).build();
}

@PutMapping("/{id}")
public ResponseEntity<Void> update(@Validated(UserDto.OnUpdate.class) @RequestBody UserDto dto) {
    // Validates only OnUpdate constraints
    return ResponseEntity.ok().build();
}
```

---

## 4. Validating nested object graphs

To validate nested child objects inside a parent DTO, you **must** place `@Valid` on the field or collection:

```java
public class OrderRequestDto {

    @NotBlank(message = "Customer ID cannot be blank")
    private String customerId;

    @NotNull(message = "Order must contain at least one item")
    @Size(min = 1, message = "Order must contain at least 1 item")
    @Valid // ⚠️ CRITICAL: Cascades validation to every item inside the list!
    private List<OrderItemDto> items;

    @NotNull
    @Valid // ⚠️ Validates nested address object!
    private AddressDto shippingAddress;
}

public class OrderItemDto {
    @NotBlank
    private String productSku;

    @Min(value = 1, message = "Quantity must be at least 1")
    private int quantity;
}
```

---

## 5. Authoring custom constraint annotations

When built-in annotations aren't enough (e.g., verifying allowed phone formats, enum values, or tax IDs), create a custom constraint annotation and validator.

``` mermaid
flowchart TD
    Annotation["1. @ValidPhoneNumber<br/><i>(Constraint Annotation)</i>"] -->|validatedBy| Validator["2. PhoneNumberValidator<br/><i>(implements ConstraintValidator)</i>"]
    Validator -->|Validates field value| Result{"isValid() ?"}
    Result -->|true| Pass["✅ Valid"]
    Result -->|false| Fail["❌ Throw Violation"]
```

### Step 1: Define the annotation
```java
package com.example.demo.validation;

import jakarta.validation.Constraint;
import jakarta.validation.Payload;
import java.lang.annotation.*;

@Documented
@Constraint(validatedBy = PhoneNumberValidator.class)
@Target({ElementType.FIELD, ElementType.PARAMETER})
@Retention(RetentionPolicy.RUNTIME)
public @interface ValidPhoneNumber {
    String message() default "Invalid international phone number format. Must start with '+' followed by 7-15 digits";
    Class<?>[] groups() default {};
    Class<? extends Payload>[] payload() default {};
}
```

### Step 2: Implement the `ConstraintValidator`
```java
package com.example.demo.validation;

import jakarta.validation.ConstraintValidator;
import jakarta.validation.ConstraintValidatorContext;
import java.util.regex.Pattern;

public class PhoneNumberValidator implements ConstraintValidator<ValidPhoneNumber, String> {

    // E.164 standard phone format: +[country code][number]
    private static final Pattern PHONE_PATTERN = Pattern.compile("^\\+[1-9]\\d{6,14}$");

    @Override
    public boolean isValid(String value, ConstraintValidatorContext context) {
        if (value == null) {
            return true; // Let @NotNull handle null checks if required
        }
        return PHONE_PATTERN.matcher(value).matches();
    }
}
```

### Step 3: USE it in DTO
```java
public record RegisterCustomerRequest(
    @NotBlank String name,
    @ValidPhoneNumber String phoneNumber
) {}
```

---

## 6. Spring Boot 3 vs Spring Boot 4: Validation engine evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        JV30["Jakarta Validation 3.0"]
        ExplicitValid["Explicit @Valid on Record Fields"]
        SeparateNullChecks["@NotNull Separated from Type System"]
    end

    subgraph SB4["Spring Boot 4.x"]
        JV31["Jakarta Validation 3.1"]
        AutoRecordCascade["Automatic Record Component Validation"]
        JSpecifyIntegration["JSpecify NonNull Integration"]
    end

    SB3 ==>|Validation Modernization| SB4
```

### Key differences and configuration comparison

| Validation Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Validation Standard** | Jakarta Bean Validation 3.0 (Hibernate Validator 8). | **Jakarta Bean Validation 3.1 (Hibernate Validator 9)**. |
| **Java Record Integration** | Required explicit `@Valid` annotation on record components for cascades. | **Native Record Cascade**: Deep validation of record components and sealed hierarchies automatically. |
| **Null-Safety Bridge** | Required redundant `@NotNull` alongside non-null type systems. | **JSpecify Type Inference**: Framework validates non-null invariants directly from JSpecify type annotations. |

---

## 7. Primary sources and further reading

- [Hibernate Validator Official Reference Guide](https://docs.jboss.org/hibernate/validator/8.0/reference/en-US/html_single/), Jakarta Validation reference implementation documentation.
- [Spring Framework Validation Documentation](https://docs.spring.io/spring-framework/reference/core/validation.html), Spring's integration with Bean Validation.
- [Jakarta Bean Validation 3.1 Specification](https://jakarta.ee/specifications/bean-validation/3.1/), Standard specification.

---

## 8. Knowledge check and practice

??? question "Question 1: What happens if you omit `@Valid` on a nested `List<OrderItemDto>` field inside a parent `OrderRequestDto`?"
    **Answer**: Hibernate Validator will only check the `@NotNull` and `@Size` on the list itself, completely skipping validation on the internal `OrderItemDto` objects.

??? question "Question 2: What is the primary difference between Jakarta `@Valid` and Spring `@Validated`?"
    **Answer**: `@Valid` is the standard annotation for triggering validation cascades on objects, while `@Validated` supports Spring Validation Groups and method-level validation on Spring Beans.

??? question "Question 3: In a custom `ConstraintValidator.isValid(String value, ...)` method, why is returning `true` for `null` values considered a best practice?"
    **Answer**: Validation constraints should adhere to the single-responsibility principle. Null checks should be left to `@NotNull` unless the annotation explicitly implies non-nullity.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0007: Building RESTful CRUD APIs**](0007-building-restful-crud-apis.md) | [**All Lessons**](index.md) | [ **0009: Global Exception Handling with @RestControllerAdvice**](0009-global-exception-handling.md) |

