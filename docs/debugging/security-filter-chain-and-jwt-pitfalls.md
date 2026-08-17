---
icon: lucide/bug
---

# Troubleshooting Spring Security 6 Filter Chains, JWT Exceptions & CORS Pitfalls

Spring Security filters execute before requests reach `DispatcherServlet`. Consequently, standard Spring MVC exception handlers (`@RestControllerAdvice`, `@ExceptionHandler`) **cannot catch** security filter exceptions by default, often causing confusing 500 errors, silent 403 authorization denials, or blocked CORS preflight requests.

This diagnostic guide walks through the root causes and production solutions for the three most common Spring Security 6 runtime pitfalls.

---

## 1. Issue 1: JWT Filter Exceptions Triggering 500 Instead of 401

### The Symptom
When a client sends an expired or tampered JWT, JJWT throws `ExpiredJwtException` or `SignatureException`. Instead of returning a clean RFC 7807 `401 Unauthorized` JSON envelope, the API crashes with an unformatted `500 Internal Server Error` and stack trace.

### Root Cause Architecture

``` mermaid
sequenceDiagram
    autonumber
    actor Client as Client App
    participant Filter as JwtAuthenticationFilter
    participant Dispatcher as DispatcherServlet
    participant Advice as @RestControllerAdvice
    participant EntryPoint as AuthenticationEntryPoint

    Client->>Filter: GET /api/orders (Expired JWT)
    Filter->>Filter: jjwt.parseSignedClaims() -> Throws ExpiredJwtException!
    
    rect rgb(255, 235, 235)
        Note over Filter,Advice: 💥 FAILS TO REACH DISPATCHERSERVLET:<br/>Filter is upstream of MVC context.<br/>@RestControllerAdvice NEVER sees this exception!
    end

    alt Unhandled in Filter
        Filter-->>Client: 500 Internal Server Error (Tomcat Default Error Page) ❌
    else Delegated via HandlerExceptionResolver
        Filter->>EntryPoint: resolver.resolveException(request, response, null, ex)
        EntryPoint->>Advice: Dispatches into MVC Global Exception Handler
        Advice-->>Client: 401 Unauthorized (Clean ProblemDetail JSON) ✅
    end
```

### The Fix: Delegating to `HandlerExceptionResolver`

Inject Spring MVC's `HandlerExceptionResolver` into `JwtAuthenticationFilter`:

```java
@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtService jwtService;
    private final UserDetailsService userDetailsService;
    private final HandlerExceptionResolver handlerExceptionResolver;

    // Inject the primary Spring MVC exception resolver
    public JwtAuthenticationFilter(
            JwtService jwtService,
            UserDetailsService userDetailsService,
            @Qualifier("handlerExceptionResolver") HandlerExceptionResolver handlerExceptionResolver) {
        this.jwtService = jwtService;
        this.userDetailsService = userDetailsService;
        this.handlerExceptionResolver = handlerExceptionResolver;
    }

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {

        final String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            filterChain.doFilter(request, response);
            return;
        }

        try {
            String jwt = authHeader.substring(7);
            String username = jwtService.extractUsername(jwt);

            if (username != null && SecurityContextHolder.getContext().getAuthentication() == null) {
                UserDetails userDetails = userDetailsService.loadUserByUsername(username);
                if (jwtService.isTokenValid(jwt, userDetails)) {
                    UsernamePasswordAuthenticationToken authToken = 
                        new UsernamePasswordAuthenticationToken(userDetails, null, userDetails.getAuthorities());
                    SecurityContextHolder.getContext().setAuthentication(authToken);
                }
            }
            filterChain.doFilter(request, response);
        } catch (Exception ex) {
            // 🛡️ Forward filter exception to @RestControllerAdvice!
            handlerExceptionResolver.resolveException(request, response, null, ex);
        }
    }
}
```

---

## 2. Issue 2: Role Prefix Mismatch Causing Silent 403 Forbidden

### The Symptom
A user possesses the role `"ADMIN"`, but calling a method annotated with `@PreAuthorize("hasRole('ADMIN')")` or hitting `.requestMatchers("/api/admin/**").hasRole("ADMIN")` consistently fails with `403 Forbidden`.

### Root Cause
Spring Security distinguishes between **Roles** and **Authorities**:
- `hasRole("ADMIN")` internally prepends `"ROLE_"`, expecting `GrantedAuthority.getAuthority()` to return `"ROLE_ADMIN"`.
- If your JWT claims or `UserDetailsService` sets authorities as `"ADMIN"` (without `ROLE_`), `hasRole("ADMIN")` returns `false`.

``` mermaid
flowchart TD
    UserAuth["GrantedAuthority in Token: 'ADMIN'"] --> Check["hasRole('ADMIN') Check"]
    Check --> Prepend["Prepend prefix: 'ROLE_' + 'ADMIN' = 'ROLE_ADMIN'"]
    Prepend --> Compare{"'ADMIN' == 'ROLE_ADMIN'?"}
    Compare -->|No Match| Denied["❌ 403 Access Denied"]
    Compare -->|Match| Granted["✅ 200 OK"]
```

### The Fix
Ensure consistent prefixing in your `UserDetailsService` or JWT converter:

```java
// ✅ CORRECT: Add "ROLE_" prefix when populating authorities
List<GrantedAuthority> authorities = user.getRoles().stream()
        .map(role -> new SimpleGrantedAuthority("ROLE_" + role))
        .collect(Collectors.toList());

// OR use hasAuthority instead of hasRole if omitting prefixes:
@PreAuthorize("hasAuthority('ADMIN')")
```

---

## 3. Issue 3: CORS Preflight `OPTIONS` Blocked by Security Filter Chain

### The Symptom
Web frontends (React/Angular) report browser console errors:  
`Access to XMLHttpRequest has been blocked by CORS policy: Response to preflight request doesn't pass access control check: It does not have HTTP ok status (401/403).`

### Root Cause
Before sending a `POST` or `PUT` request with custom headers (like `Authorization: Bearer`), the browser sends an HTTP `OPTIONS` preflight request. If Spring Security processes authorization before CORS, the preflight request lacks credentials and gets rejected with 401/403.

### The Fix: Explicitly Enable CORS & Allow `OPTIONS`
In Spring Security 6, `.cors()` must be declared on `HttpSecurity` alongside a configured `CorsConfigurationSource`:

```java
@Bean
public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
    return http
        // 1. Enable CORS at the beginning of the chain
        .cors(Customizer.withDefaults())
        .csrf(AbstractHttpConfigurer::disable)
        .authorizeHttpRequests(auth -> auth
            // Explicitly allow all preflight OPTIONS requests if needed
            .requestMatchers(HttpMethod.OPTIONS, "/**").permitAll()
            .requestMatchers("/api/public/**").permitAll()
            .anyRequest().authenticated()
        )
        .build();
}

@Bean
public CorsConfigurationSource corsConfigurationSource() {
    CorsConfiguration config = new CorsConfiguration();
    config.setAllowedOrigins(List.of("http://localhost:3000", "https://app.example.com"));
    config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"));
    config.setAllowedHeaders(List.of("Authorization", "Content-Type", "X-Correlation-ID"));
    config.setAllowCredentials(true);
    config.setMaxAge(3600L); // Cache preflight for 1 hour

    UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
    source.registerCorsConfiguration("/**", config);
    return source;
}
```

---

## 🧭 Navigation & Diagnostic Playbooks

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Troubleshooting Actuator Exposure & MDC Leaks**](actuator-security-and-logging-leaks.md) | [**All Debugging Guides**](index.md) | [➡️ **Jib Auth & GraalVM Native Troubleshooting**](jib-cloud-auth-and-graalvm-native-pitfalls.md) |
