---
icon: lucide/shield
---

# Spring Security 6, JWT & OAuth2 Cheatsheet

A rapid-reference guide for modern Spring Security 6 component-based configuration, `SecurityFilterChain` bean declarations, SpEL method authorization, JJWT generation/validation, and OAuth2 Client properties.

---

## 1. Modern Stateless `SecurityFilterChain` Bean

```java
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(
            HttpSecurity http, 
            JwtAuthenticationFilter jwtAuthFilter,
            AuthenticationEntryPoint authEntryPoint) throws Exception {
        return http
            .csrf(AbstractHttpConfigurer::disable)
            .cors(Customizer.withDefaults())
            .exceptionHandling(ex -> ex.authenticationEntryPoint(authEntryPoint))
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**", "/public/**", "/swagger-ui/**", "/v3/api-docs/**").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/products/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .requestMatchers("/api/manager/**").hasAnyRole("MANAGER", "ADMIN")
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class)
            .build();
    }
}
```

---

## 2. Password Encoder Configuration (Argon2id + BCrypt)

```java
@Configuration
public class PasswordConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        String defaultEncodingId = "argon2";
        Map<String, PasswordEncoder> encoders = new HashMap<>();
        encoders.put("argon2", new Argon2PasswordEncoder(16, 32, 1, 65536, 3));
        encoders.put("bcrypt", new BCryptPasswordEncoder(12));

        DelegatingPasswordEncoder delegating = new DelegatingPasswordEncoder(defaultEncodingId, encoders);
        delegating.setDefaultPasswordEncoderForMatches(new BCryptPasswordEncoder(10));
        return delegating;
    }
}
```

---

## 3. Method Security & SpEL Expressions (`@PreAuthorize`)

Enable with `@EnableMethodSecurity(prePostEnabled = true)`:

| SpEL Expression | Security Enforcement Check |
| :--- | :--- |
| `@PreAuthorize("hasRole('ADMIN')")` | Checks for `ROLE_ADMIN` authority. |
| `@PreAuthorize("hasAnyRole('USER', 'EDITOR')")` | Checks for either `ROLE_USER` or `ROLE_EDITOR`. |
| `@PreAuthorize("hasAuthority('order:delete')")` | Checks for explicit permission `order:delete`. |
| `@PreAuthorize("#id == authentication.principal.id")` | Checks if method argument `#id` matches authenticated user ID. |
| `@PreAuthorize("@authService.isOwner(#orderId, principal)")` | Delegates authorization check to a custom Spring bean. |
| `@PostAuthorize("returnObject.owner == principal.username")` | Inspects returned object before sending response to caller. |

---

## 4. JJWT 0.12+ Token Generation & Parsing

```java
// 1. Generate Token with Claims & Expiration:
SecretKey key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
String jwt = Jwts.builder()
    .subject(username)
    .claim("roles", List.of("ROLE_USER"))
    .issuedAt(new Date())
    .expiration(new Date(System.currentTimeMillis() + 900_000)) // 15 mins
    .signWith(key)
    .compact();

// 2. Parse & Validate Token Claims:
Claims claims = Jwts.parser()
    .verifyWith(key)
    .build()
    .parseSignedClaims(jwt)
    .getPayload();

String subject = claims.getSubject();
Date expiration = claims.getExpiration();
```

---

## 5. Spring Boot OAuth2 Client Properties (`application.yml`)

```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          google:
            client-id: ${GOOGLE_CLIENT_ID}
            client-secret: ${GOOGLE_CLIENT_SECRET}
            scope: [openid, profile, email]
            redirect-uri: "{baseUrl}/login/oauth2/code/{registrationId}"
          github:
            client-id: ${GITHUB_CLIENT_ID}
            client-secret: ${GITHUB_CLIENT_SECRET}
            scope: [read:user, user:email]
```

---

## 🧭 Navigation & Cheatsheet Index

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Spring Observability & Logging Cheatsheet**](spring-observability-devtools.md) | [**All Cheatsheets**](index.md) | *(Module 6 Testing Cheatsheet Coming Soon)* |
