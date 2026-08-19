---
icon: lucide/shield-check
---

# 0023: Spring Security 6 architecture: Filter chains, AuthenticationManager, and SecurityContext

In enterprise web applications, security is not a single checkpoint, it is a layered pipeline that enforces **Authentication** *(Who are you?)* and **Authorization** *(What are you allowed to do?)* before requests ever reach your controller endpoints.

Spring Security 6 (shipped with Spring Boot 3.x) completely modernizes framework security by eliminating legacy adapter classes (such as `WebSecurityConfigurerAdapter`) in favor of component-based bean declarations and lambda DSLs. In this lesson, you will master the internal architecture of Spring Security 6, understand how the servlet filter chain delegates to Spring-managed beans, and build a modern security configuration from first principles.

---

## 1. The security filter chain pipeline

Spring Security sits in the Servlet filter pipeline in front of `DispatcherServlet`. Because the servlet container (e.g., Tomcat) has its own lifecycle independent of the Spring IoC `ApplicationContext`, Spring bridges this gap using `DelegatingFilterProxy`.

``` mermaid
flowchart TD
    Client["🌐 Client (Browser / Mobile / cURL)"] -->|HTTP Request| Tomcat["Tomcat Servlet Container"]

    subgraph StandardServletFilters["Standard Servlet Filter Pipeline"]
        F1["LoggingFilter"]
        Proxy["DelegatingFilterProxy<br/><i>(Standard Servlet Filter)</i>"]
        F2["CustomHeaderFilter"]
    end

    subgraph SpringContext["Spring ApplicationContext"]
        FCP["FilterChainProxy<br/><code>springSecurityFilterChain</code>"]
        
        subgraph SecurityFilterChain["SecurityFilterChain (Ordered Filters)"]
            SF1["1. SecurityContextHolderFilter<br/><i>(Restores SecurityContext)</i>"]
            SF2["2. HeaderWriterFilter<br/><i>(X-Frame-Options, CSP)</i>"]
            SF3["3. CsrfFilter<br/><i>(Validates CSRF tokens)</i>"]
            SF4["4. UsernamePasswordAuthenticationFilter<br/><i>(or custom JwtAuthFilter)</i>"]
            SF5["5. ExceptionTranslationFilter<br/><i>(Translates 401/403)</i>"]
            SF6["6. AuthorizationFilter<br/><i>(Checks roles & permissions)</i>"]
        end
    end

    Tomcat --> F1
    F1 --> Proxy
    Proxy -->|Delegates to Spring Bean| FCP
    FCP --> SF1
    SF1 --> SF2 --> SF3 --> SF4 --> SF5 --> SF6
    SF6 --> F2
    F2 -->|Authorized Request| DS["DispatcherServlet & @RestController"]

    StandardServletFilters ~~~ SpringContext ~~~ SecurityFilterChain
```

### How the bridge works
1. **`DelegatingFilterProxy`**: A standard `jakarta.servlet.Filter` registered in the container that looks up a Spring bean named `springSecurityFilterChain` from the `ApplicationContext` and delegates all work to it.
2. **`FilterChainProxy`**: The master Spring bean that coordinates one or more `SecurityFilterChain` instances based on `RequestMatcher` patterns (e.g., one chain for `/api/**` and another for `/oauth2/**`).
3. **`SecurityFilterChain`**: An ordered list of security filters that execute sequentially for each incoming HTTP request.

---

## 2. The core security domain objects

``` mermaid
classDiagram
    class SecurityContextHolder {
        +getContext() SecurityContext
        +setContext(SecurityContext)
        +clearContext()
    }
    class SecurityContext {
        +getAuthentication() Authentication
        +setAuthentication(Authentication)
    }
    class Authentication {
        +getPrincipal() Object
        +getCredentials() Object
        +getAuthorities() Collection~GrantedAuthority~
        +isAuthenticated() boolean
    }
    class UserDetails {
        +getUsername() String
        +getPassword() String
        +getAuthorities() Collection~GrantedAuthority~
        +isAccountNonExpired() boolean
        +isAccountNonLocked() boolean
        +isEnabled() boolean
    }
    class GrantedAuthority {
        +getAuthority() String
    }

    SecurityContextHolder --> SecurityContext : holds
    SecurityContext --> Authentication : contains
    Authentication ..> GrantedAuthority : has many
    Authentication ..> UserDetails : principal often implements
```

- **`SecurityContextHolder`**: Provides access to the current `SecurityContext`. By default, it stores state in a `ThreadLocal` variable (per-thread isolation).
- **`SecurityContext`**: Holds the currently authenticated `Authentication` object.
- **`Authentication`**: Represents the token for an authentication request or an authenticated principal. Holds the principal (user identity), credentials (password/token), and authorities (roles/permissions).
- **`UserDetails`**: The core user interface that provides identity and credential details to Spring Security.
- **`GrantedAuthority`**: An individual permission or role granted to the principal (e.g., `ROLE_ADMIN`, `order:write`).

---

## 3. The authentication engine internals

When a user submits credentials, the authentication workflow flows through `AuthenticationManager`, `AuthenticationProvider`, and `UserDetailsService`:

``` mermaid
sequenceDiagram
    autonumber
    actor Client as Client / API Caller
    participant Filter as UsernamePasswordAuthenticationFilter
    participant AuthManager as AuthenticationManager (ProviderManager)
    participant Provider as DaoAuthenticationProvider
    participant Service as UserDetailsService
    participant Encoder as PasswordEncoder
    participant Context as SecurityContextHolder

    Client->>Filter: POST /login (username, password)
    Filter->>Filter: Creates unauthenticated UsernamePasswordAuthenticationToken
    Filter->>AuthManager: authenticate(unauthenticatedToken)
    AuthManager->>Provider: authenticate(unauthenticatedToken)
    Provider->>Service: loadUserByUsername("alice")
    Service-->>Provider: Returns UserDetails (with hashed password & roles)
    Provider->>Encoder: matches(rawPassword, encodedPassword)
    
    alt Password Matches
        Encoder-->>Provider: true
        Provider->>Provider: Creates authenticated UsernamePasswordAuthenticationToken
        Provider-->>AuthManager: Returns fully populated Authentication
        AuthManager-->>Filter: Returns Authentication
        Filter->>Context: SecurityContextHolder.getContext().setAuthentication(auth)
        Filter-->>Client: 200 OK (or Session / JWT Token)
    else Password Mismatch / User Not Found
        Encoder-->>Provider: false
        Provider-->>Filter: Throws BadCredentialsException
        Filter-->>Client: 401 Unauthorized
    end
```

---

## 4. Modern Spring security 6 configuration

In Spring Security 6, you configure security by declaring a `@Bean` of type `SecurityFilterChain`. The legacy `WebSecurityConfigurerAdapter` has been removed.

### `SecurityConfig.java`
```java
package com.example.security.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.ProviderManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

import java.util.List;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            // 1. Disable CSRF for stateless REST APIs
            .csrf(AbstractHttpConfigurer::disable)
            
            // 2. Configure endpoint authorization rules
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**", "/swagger-ui/**", "/v3/api-docs/**").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/products/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .requestMatchers("/api/orders/**").hasAnyRole("USER", "ADMIN")
                .anyRequest().authenticated()
            )
            
            // 3. Configure HTTP Basic Authentication (or JWT filter)
            .httpBasic(Customizer.withDefaults())
            
            // 4. Session Management: STATELESS for REST APIs
            .sessionManagement(session -> 
                session.sessionCreationPolicy(SessionCreationPolicy.STATELESS)
            );

        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder(12); // Work factor = 12
    }

    @Bean
    public UserDetailsService userDetailsService(PasswordEncoder passwordEncoder) {
        UserDetails admin = User.builder()
            .username("admin")
            .password(passwordEncoder.encode("SecretAdmin123!"))
            .roles("ADMIN") // Automatically prefixed as "ROLE_ADMIN"
            .build();

        UserDetails user = User.builder()
            .username("alice")
            .password(passwordEncoder.encode("UserPass123!"))
            .roles("USER")
            .build();

        return new InMemoryUserDetailsManager(admin, user);
    }

    @Bean
    public AuthenticationManager authenticationManager(
            UserDetailsService userDetailsService,
            PasswordEncoder passwordEncoder) {
        DaoAuthenticationProvider authProvider = new DaoAuthenticationProvider();
        authProvider.setUserDetailsService(userDetailsService);
        authProvider.setPasswordEncoder(passwordEncoder);
        return new ProviderManager(List.of(authProvider));
    }
}
```

---

## 5. Securitycontext in multi-threaded async environments

By default, `SecurityContextHolder` uses a `ThreadLocal` strategy (`MODE_THREADLOCAL`). If your application invokes `@Async` background tasks or passes execution to an `ExecutorService`, the child thread will **not** inherit the security context unless explicitly configured:

| SecurityContextHolder Strategy | How It Works | Use Case |
| :--- | :--- | :--- |
| `MODE_THREADLOCAL` *(Default)* | Security context is bound strictly to the current request thread. | Standard web requests. |
| `MODE_INHERITABLETHREADLOCAL` | Context is automatically passed to child threads spawned by the current thread. | Multi-threaded parent-child batch processing. |
| `DelegatingSecurityContextAsyncTaskExecutor` | Wraps Spring `TaskExecutor` to automatically propagate context to thread pool workers. | Production `@Async` methods & CompletableFutures. |

```java
@Configuration
@EnableAsync
public class AsyncSecurityConfig {

    @Bean
    public TaskExecutor threadPoolTaskExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(5);
        executor.setMaxPoolSize(20);
        executor.setThreadNamePrefix("async-sec-");
        executor.initialize();
        
        // Wraps tasks so SecurityContext propagates cleanly across thread boundaries
        return new DelegatingSecurityContextAsyncTaskExecutor(executor);
    }
}
```

---

## 6. Spring Boot 3 (security 6) vs Spring Boot 4 (security 7) evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Spring Security 6)"]
        LambdaDSL["HttpSecurity Lambda DSL (Customizer.withDefaults)"]
        TLContext["ThreadLocal SecurityContextHolder"]
        ExplicitStateless["Explicit sessionCreationPolicy(STATELESS)"]
    end

    subgraph SB4["Spring Boot 4.x (Spring Security 7)"]
        FluentChain["Simplified Declarative Filter Chains"]
        ScopedValSec["ScopedValue SecurityContext (Loom Native)"]
        StatelessDefault["Stateless by Default for REST Web MVC"]
    end

    SB3 ==>|Security Modernization| SB4
```

### Key differences and configuration comparison

| Security Capability | Spring Boot 3.x (Security 6) | Spring Boot 4.x (Security 7) |
| :--- | :--- | :--- |
| **Security Context Strategy** | `ThreadLocal` (`MODE_THREADLOCAL`). Required `DelegatingSecurityContextAsyncTaskExecutor` for background threads. | **`ScopedValue` Security Context**: Native Virtual Thread propagation without thread pool pollution or memory leaks. |
| **Default Session Policy** | `SessionCreationPolicy.IF_REQUIRED` (creates `JSESSIONID` unless explicitly configured stateless). | **Smart Protocol Defaults**: Automatically applies stateless token handling when REST controllers are detected. |
| **Configuration DSL** | Lambda DSL (`http.csrf(AbstractHttpConfigurer::disable)`). | **Streamlined Fluent DSL**: Deprecated legacy configurers removed; cleaner one-line method chaining. |

---

## 7. Primary sources and further reading

- [Spring Security 6 Official Architecture Documentation](https://docs.spring.io/spring-security/reference/servlet/architecture.html), Deep dive into `FilterChainProxy`, `SecurityFilterChain`, and request dispatching.
- [Spring Security 7 Next-Gen Architecture Vision](https://github.com/spring-projects/spring-security/wiki), Project Loom scoped security context integration.
- [Spring Boot 3 Migration Guide for Security](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide#spring-security), Architectural migration away from deprecated adapters.

---

## 8. Knowledge check and practice

??? question "Question 1: What is the exact role of `DelegatingFilterProxy` in the Spring Security filter pipeline?"
    **Answer**: It acts as a bridge between the Servlet container's standard filter lifecycle and Spring's `ApplicationContext`, delegating request processing to the Spring-managed `FilterChainProxy` bean named `springSecurityFilterChain`.

??? question "Question 2: Why does calling `.roles(\"ADMIN\")` on `User.builder()` result in an authority named `ROLE_ADMIN`?"
    **Answer**: Spring Security automatically prefixes role names with the `ROLE_` prefix when using role-based methods (`hasRole`), distinguishing coarse-grained roles from fine-grained authorities/permissions (`hasAuthority`).

??? question "Question 3: If a background thread spawned by `@Async` tries to read `SecurityContextHolder.getContext().getAuthentication()`, why does it return null by default?"
    **Answer**: By default, `SecurityContextHolder` uses a standard `ThreadLocal` strategy that isolates state to the calling request thread; background worker threads in a pool require a `DelegatingSecurityContextAsyncTaskExecutor` to propagate the context.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0022: Centralized Logging & ELK**](0022-centralized-logging-elk-stack.md) | [**All Lessons**](index.md) | [ **0024: Password Hashing & Sessions**](0024-password-hashing-bcrypt-argon2-sessions.md) |
