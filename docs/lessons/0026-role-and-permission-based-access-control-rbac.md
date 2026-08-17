---
icon: lucide/shield-alert
---

# 0026: Role-Based & Permission-Based Access Control (RBAC) with Method Security (`@PreAuthorize`)

Authentication verifies identity, but **Authorization** dictates what resources and operations that identity can access. While URL-based request matching protects public routes, enterprise domain logic often demands fine-grained, contextual permissions (e.g., *"A manager can approve orders up to $10,000, but only the creator or an Admin can delete an order"*).

In Spring Security 6, **Method Security** replaces and enhances legacy security models using AOP proxies and Spring Expression Language (SpEL). In this lesson, you will master the difference between Roles and Authorities, configure `@EnableMethodSecurity`, enforce domain-level ownership checks with `@PreAuthorize` and `@PostAuthorize`, and implement custom security evaluator beans.

---

## 1. Roles vs Permissions (Authorities) Architecture

In enterprise security architectures, hardcoding coarse roles throughout business logic creates brittle systems. Modern systems decouple **Roles** (user groups) from **Permissions** (fine-grained capabilities):

``` mermaid
flowchart TD
    subgraph Users["Principals (Users)"]
        U1["User: Alice"]
        U2["User: Bob (Manager)"]
    end

    subgraph Roles["Coarse-Grained Roles"]
        R_USER["ROLE_USER"]
        R_ADMIN["ROLE_ADMIN"]
    end

    subgraph Authorities["Fine-Grained Permissions (Authorities)"]
        P1["order:read"]
        P2["order:create"]
        P3["order:cancel"]
        P4["order:refund"]
        P5["user:delete"]
    end

    U1 --> R_USER
    U2 --> R_ADMIN

    R_USER --> P1
    R_USER --> P2
    
    R_ADMIN --> P1
    R_ADMIN --> P2
    R_ADMIN --> P3
    R_ADMIN --> P4
    R_ADMIN --> P5
```

### Prefix Convention in Spring Security
- **Role (`hasRole('ADMIN')`)**: Spring automatically prefixes with `ROLE_`, looking for `ROLE_ADMIN` in `GrantedAuthority`.
- **Authority (`hasAuthority('order:refund')`)**: Exact string match without prefix modification.

---

## 2. Enabling Modern Method Security in Spring Security 6

In Spring Security 6, `@EnableGlobalMethodSecurity` is deprecated in favor of `@EnableMethodSecurity` (which enables `@PreAuthorize`, `@PostAuthorize`, `@PreFilter`, and `@PostFilter` by default):

```java
package com.example.security.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;

@Configuration
@EnableMethodSecurity(prePostEnabled = true, securedEnabled = true, jsr250Enabled = true)
public class MethodSecurityConfig {
    // Enables @PreAuthorize, @Secured, and @RolesAllowed
}
```

---

## 3. The Method Security AOP Interception Pipeline

Method security uses Spring AOP proxies around your service or controller beans:

``` mermaid
sequenceDiagram
    autonumber
    actor Caller as Controller / Service Caller
    participant Proxy as CGLIB Security Method Proxy
    participant Interceptor as AuthorizationManagerBeforeMethodInterceptor
    participant SpEL as SpEL EvaluationContext
    participant Target as OrderServiceImpl (Target Bean)

    Caller->>Proxy: cancelOrder(orderId=42)
    Proxy->>Interceptor: Intercept before method execution
    Interceptor->>SpEL: Evaluate @PreAuthorize("@orderSecurity.isOwner(#orderId, principal)")
    
    alt SpEL Expression Returns true
        SpEL-->>Interceptor: Access Granted (true)
        Interceptor->>Target: target.cancelOrder(42)
        Target-->>Proxy: Returns Cancelled Order DTO
        Proxy-->>Caller: 200 OK
    else SpEL Expression Returns false
        SpEL-->>Interceptor: Access Denied (false)
        Interceptor-->>Caller: Throws AccessDeniedException (403 Forbidden)
    end
```

---

## 4. Practical Method Security Annotations

### 1. `@PreAuthorize`: Enforcing Checks Before Invocation
Evaluates expressions before the method body runs. Perfect for role, authority, and argument checks.

```java
package com.example.security.service;

import com.example.security.dto.OrderResponse;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.stereotype.Service;

@Service
public class OrderService {

    // 1. Role-based check
    @PreAuthorize("hasRole('ADMIN')")
    public void purgeAllOrders() {
        // Only users with ROLE_ADMIN
    }

    // 2. Fine-grained authority check
    @PreAuthorize("hasAuthority('order:refund')")
    public void refundOrder(Long orderId, Double amount) {
        // Users with specific permission
    }

    // 3. SpEL Parameter Inspection: User can only access their own profile
    @PreAuthorize("#username == authentication.principal.username or hasRole('ADMIN')")
    public OrderResponse getOrdersForUser(String username) {
        return null;
    }
}
```

### 2. `@PostAuthorize`: Inspecting Return Values
Evaluates expressions *after* the method completes. It provides access to the returned object via the built-in `returnObject` variable:

```java
    // Only return the sensitive invoice if the caller is the owner or an accountant
    @PostAuthorize("returnObject.ownerId == authentication.principal.id or hasAuthority('invoice:audit')")
    public Invoice getInvoiceById(Long invoiceId) {
        return invoiceRepository.findById(invoiceId)
                .orElseThrow(() -> new ResourceNotFoundException("Invoice not found"));
    }
```

> [!WARNING]
> If `@PostAuthorize` fails, Spring Security throws an `AccessDeniedException` and prevents the caller from seeing the return value. However, any database modifications inside a `@Transactional` method will **already have executed** unless rolled back. Use `@PreAuthorize` for state-modifying operations.

---

## 5. Domain-Level Ownership Checks with Custom SpEL Beans

For complex business authorization (e.g., verifying database ownership across tenant partitions), avoid giant SpEL strings. Delegate to a dedicated Spring Security bean:

### `OrderSecurityService.java`
```java
package com.example.security.service;

import com.example.security.repository.OrderRepository;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Component;

@Component("orderSecurity")
public class OrderSecurityService {

    private final OrderRepository orderRepository;

    public OrderSecurityService(OrderRepository orderRepository) {
        this.orderRepository = orderRepository;
    }

    public boolean isOrderOwner(Long orderId, Authentication authentication) {
        if (authentication == null || !authentication.isAuthenticated()) {
            return false;
        }

        // Admins can bypass ownership checks
        boolean isAdmin = authentication.getAuthorities().stream()
                .anyMatch(a -> a.getAuthority().equals("ROLE_ADMIN"));
        if (isAdmin) {
            return true;
        }

        String currentUsername = authentication.getName();
        return orderRepository.findById(orderId)
                .map(order -> order.getOwnerUsername().equals(currentUsername))
                .orElse(false);
    }
}
```

### Usage in Service / Controller:
```java
@RestController
@RequestMapping("/api/orders")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @DeleteMapping("/{orderId}")
    @PreAuthorize("@orderSecurity.isOrderOwner(#orderId, authentication)")
    public ResponseEntity<Void> cancelOrder(@PathVariable Long orderId) {
        orderService.cancelOrder(orderId);
        return ResponseEntity.noContent().build();
    }
}
```

---

## 6. Primary Sources & Further Reading

- [Spring Security 6 Method Security Documentation](https://docs.spring.io/spring-security/reference/servlet/authorization/method-security.html) — Architecture of before/after method interceptors.
- [Spring Expression Language (SpEL) Security Expressions](https://docs.spring.io/spring-security/reference/servlet/authorization/expression-based.html) — Built-in variables (`authentication`, `principal`, `hasRole`, `hasAuthority`).
- [AuthorizationManager Architecture in Spring Security 6](https://docs.spring.io/spring-security/reference/servlet/authorization/architecture.html) — Modern replacement for legacy `AccessDecisionManager`.

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the fundamental difference between `hasRole('MANAGER')` and `hasAuthority('MANAGER')` in SpEL expressions?"
    **Answer**: `hasRole('MANAGER')` automatically looks for a `GrantedAuthority` with the `ROLE_` prefix (`ROLE_MANAGER`), whereas `hasAuthority('MANAGER')` checks for the literal string `MANAGER` without prefixing.

??? question "Question 2: Why should `@PostAuthorize` generally be avoided on state-modifying database write methods (`POST`/`PUT`/`DELETE`)?"
    **Answer**: Because `@PostAuthorize` executes after the method finishes; if a transaction committed changes to the database, an authorization failure prevents returning the response but will not undo the write unless an explicit rollback is triggered.

??? question "Question 3: How does referencing `@orderSecurity.isOwner(#orderId, authentication)` in `@PreAuthorize` enhance clean code architecture?"
    **Answer**: It encapsulates complex multi-table ownership, tenancy, and domain rules inside a dedicated, testable Spring bean rather than cluttering annotations with messy SpEL expressions.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0025: Stateless JWT Authentication**](0025-stateless-jwt-authentication-filter.md) | [**All Lessons**](index.md) | [➡️ **0027: Google OAuth2 & OIDC**](0027-google-oauth2-and-openid-connect-oidc.md) |
