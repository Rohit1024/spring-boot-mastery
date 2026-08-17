---
icon: lucide/lock
---

# 0025: Stateless Authentication with JWT (JSON Web Tokens): Issuing, Validating & Filter Interception

In distributed microservices and modern single-page applications (SPAs), maintaining stateful server sessions (`JSESSIONID`) requires sticky sessions or shared distributed session caches (e.g., Redis). 

**Stateless Authentication with JSON Web Tokens (JWT)** eliminates server-side session state entirely. Each cryptographically signed token encapsulates user identity, roles, and expiration. In this lesson, you will dissect the internal structure of a JWT, build a production-grade `JwtAuthenticationFilter` using `OncePerRequestFilter`, wire it into Spring Security 6's filter chain, and implement Refresh Token rotation with Redis revocation.

---

## 1. Anatomy of a JSON Web Token (JWT)

A JWT (RFC 7519) is a compact, URL-safe string composed of three Base64URL-encoded segments separated by periods (`.`):

$$\text{JWT} = \text{Base64Url}(\text{Header}) + "." + \text{Base64Url}(\text{Payload}) + "." + \text{Signature}$$

``` mermaid
flowchart TD
    subgraph JWT["JSON Web Token (Compact Encoded String)"]
        H["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9<br/><b>Header</b>"]
        P["eyJzdWIiOiIxMjM0NTYiLCJuYW1lIjoiQWxpY2UiLCJyb2xlcyI6WyJST0xFX1VTRVIiXX0<br/><b>Payload (Claims)</b>"]
        S["SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c<br/><b>Digital Signature</b>"]
    end

    H --- P --- S

    subgraph SignatureFormula["Cryptographic Signature Generation (HMAC-SHA256)"]
        Calc["HMACSHA256(<br/>&nbsp;&nbsp;base64UrlEncode(Header) + '.' + base64UrlEncode(Payload),<br/>&nbsp;&nbsp;256-bit-secret-key<br/>)"]
    end

    JWT ~~~ SignatureFormula
```

### Standard Claims vs Custom Claims
- **Standard Claims (Registered)**:
  - `sub` (Subject): Unique user ID or username.
  - `iat` (Issued At): Unix timestamp when issued.
  - `exp` (Expiration Time): Unix timestamp when token expires.
- **Custom Claims**:
  - `roles`: e.g., `["ROLE_ADMIN", "ROLE_USER"]`
  - `tenantId`: Multi-tenancy identifier.

---

## 2. Stateless JWT Request Interception Flow

``` mermaid
sequenceDiagram
    autonumber
    actor Client as SPA / Mobile Client
    participant Filter as JwtAuthenticationFilter (OncePerRequestFilter)
    participant JwtService as JwtService (Parser & Validator)
    participant UserDetails as CustomUserDetailsService
    participant Context as SecurityContextHolder
    participant Controller as @RestController Endpoint

    Client->>Filter: GET /api/orders (Header: Authorization: Bearer <jwt>)
    Filter->>Filter: Extract Bearer token from header
    
    alt Token Present & Valid
        Filter->>JwtService: extractUsername(token) & isTokenValid(token)
        JwtService-->>Filter: Claims valid (sub="alice", not expired)
        Filter->>UserDetails: loadUserByUsername("alice")
        UserDetails-->>Filter: UserDetails (alice, [ROLE_USER])
        Filter->>Context: setAuthentication(UsernamePasswordAuthenticationToken)
        Filter->>Controller: chain.doFilter(request, response)
        Controller-->>Client: 200 OK (Orders JSON)
    else Token Expired or Invalid Signature
        Filter-->>Client: 401 Unauthorized (via JwtAuthenticationEntryPoint)
    else No Token on Public Route
        Filter->>Controller: Passes through to AuthorizationFilter
    end
```

---

## 3. Production JWT Implementation with JJWT 0.12+

### Dependencies (`pom.xml`)
```xml
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-api</artifactId>
    <version>0.12.6</version>
</dependency>
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-impl</artifactId>
    <version>0.12.6</version>
    <scope>runtime</scope>
</dependency>
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt-jackson</artifactId>
    <version>0.12.6</version>
    <scope>runtime</scope>
</dependency>
```

### 1. `JwtService.java` (Token Utility)
```java
package com.example.security.jwt;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;

@Service
public class JwtService {

    private final SecretKey signingKey;
    private final long jwtExpirationMs;

    public JwtService(
            @Value("${application.security.jwt.secret-key}") String secretKey,
            @Value("${application.security.jwt.expiration-ms:900000}") long jwtExpirationMs) { // 15 min default
        this.signingKey = Keys.hmacShaKeyFor(secretKey.getBytes(StandardCharsets.UTF_8));
        this.jwtExpirationMs = jwtExpirationMs;
    }

    public String generateToken(UserDetails userDetails) {
        Map<String, Object> extraClaims = new HashMap<>();
        List<String> roles = userDetails.getAuthorities().stream()
                .map(GrantedAuthority::getAuthority)
                .toList();
        extraClaims.put("roles", roles);

        return Jwts.builder()
                .claims(extraClaims)
                .subject(userDetails.getUsername())
                .issuedAt(new Date(System.currentTimeMillis()))
                .expiration(new Date(System.currentTimeMillis() + jwtExpirationMs))
                .signWith(signingKey)
                .compact();
    }

    public String extractUsername(String token) {
        return extractClaim(token, Claims::getSubject);
    }

    public boolean isTokenValid(String token, UserDetails userDetails) {
        final String username = extractUsername(token);
        return (username.equals(userDetails.getUsername())) && !isTokenExpired(token);
    }

    private boolean isTokenExpired(String token) {
        return extractExpiration(token).before(new Date());
    }

    private Date extractExpiration(String token) {
        return extractClaim(token, Claims::getExpiration);
    }

    public <T> T extractClaim(String token, Function<Claims, T> claimsResolver) {
        final Claims claims = extractAllClaims(token);
        return claimsResolver.apply(claims);
    }

    private Claims extractAllClaims(String token) {
        return Jwts.parser()
                .verifyWith(signingKey)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}
```

### 2. `JwtAuthenticationFilter.java` (`OncePerRequestFilter`)
```java
package com.example.security.jwt;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.lang.NonNull;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtService jwtService;
    private final UserDetailsService userDetailsService;

    public JwtAuthenticationFilter(JwtService jwtService, UserDetailsService userDetailsService) {
        this.jwtService = jwtService;
        this.userDetailsService = userDetailsService;
    }

    @Override
    protected void doFilterInternal(
            @NonNull HttpServletRequest request,
            @NonNull HttpServletResponse response,
            @NonNull FilterChain filterChain) throws ServletException, IOException {

        final String authHeader = request.getHeader("Authorization");
        final String jwt;
        final String username;

        // 1. Check if Authorization header is present with "Bearer "
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            filterChain.doFilter(request, response);
            return;
        }

        jwt = authHeader.substring(7); // Remove "Bearer " prefix

        try {
            username = jwtService.extractUsername(jwt);

            // 2. Validate token only if not already authenticated in this thread
            if (username != null && SecurityContextHolder.getContext().getAuthentication() == null) {
                UserDetails userDetails = this.userDetailsService.loadUserByUsername(username);

                if (jwtService.isTokenValid(jwt, userDetails)) {
                    UsernamePasswordAuthenticationToken authToken = new UsernamePasswordAuthenticationToken(
                            userDetails,
                            null,
                            userDetails.getAuthorities()
                    );
                    authToken.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
                    
                    // 3. Populate SecurityContextHolder
                    SecurityContextHolder.getContext().setAuthentication(authToken);
                }
            }
        } catch (Exception ex) {
            // Token parsing or signature verification failed
            logger.warn("JWT token verification failed: " + ex.getMessage());
        }

        filterChain.doFilter(request, response);
    }
}
```

### 3. Integrating the Filter in `SecurityConfig.java`
```java
package com.example.security.config;

import com.example.security.jwt.JwtAuthenticationEntryPoint;
import com.example.security.jwt.JwtAuthenticationFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthFilter;
    private final JwtAuthenticationEntryPoint authEntryPoint;

    public SecurityConfig(JwtAuthenticationFilter jwtAuthFilter, JwtAuthenticationEntryPoint authEntryPoint) {
        this.jwtAuthFilter = jwtAuthFilter;
        this.authEntryPoint = authEntryPoint;
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .exceptionHandling(ex -> ex.authenticationEntryPoint(authEntryPoint))
            .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/auth/**", "/swagger-ui/**", "/v3/api-docs/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            // Insert custom JWT filter before the standard UsernamePasswordAuthenticationFilter
            .addFilterBefore(jwtAuthFilter, UsernamePasswordAuthenticationFilter.class);

        return http.build();
    }
}
```

---

## 4. Access Token + Refresh Token Rotation Strategy

Because JWTs are stateless, you cannot "delete" a valid JWT once issued until it expires. To balance security and user experience:

``` mermaid
sequenceDiagram
    autonumber
    actor Client as Client App
    participant Auth as Auth Server (/api/auth)
    participant Redis as Redis Cache (Revocation List)
    participant API as Resource API

    Client->>Auth: POST /api/auth/login (username, password)
    Auth->>Auth: Validates credentials
    Auth-->>Client: Returns AccessToken (15m) + RefreshToken (7d)
    
    Client->>API: GET /api/data (Header: Bearer <AccessToken>)
    API-->>Client: 200 OK
    
    Note over Client,API: 15 minutes pass -> AccessToken expires
    
    Client->>API: GET /api/data (Expired AccessToken)
    API-->>Client: 401 Unauthorized (Token Expired)
    
    Client->>Auth: POST /api/auth/refresh (RefreshToken)
    Auth->>Redis: Check if RefreshToken is revoked / already used
    alt RefreshToken Valid
        Auth->>Redis: Rotate / Invalidate old RefreshToken
        Auth-->>Client: Returns NEW AccessToken (15m) + NEW RefreshToken (7d)
    else Reuse Detected (Compromised)
        Auth->>Redis: Revoke entire token family!
        Auth-->>Client: 403 Forbidden
    end
```

---

## 5. Spring Boot 3 vs Spring Boot 4: JWT & Resource Server Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Security 6)"]
        ManualFilter["Custom OncePerRequestFilter with JJWT Parser"]
        ManualContext["Manual SecurityContextHolder.setAuthentication()"]
        SeparateRedisRevoke["Custom Redis Template Blacklist Filter"]
    end

    subgraph SB4["Spring Boot 4.x (Security 7)"]
        DeclarativeResourceServer["Declarative oauth2ResourceServer().jwt()"]
        NativeJwksRotation["Zero-Boilerplate JWKS & Key Rotation"]
        ScopedAuthToken["ScopedValue-Bound Principal Context"]
    end

    SB3 ==>|Filterless Modernization| SB4
```

### Key Differences & Configuration Comparison

| JWT Security Feature | Spring Boot 3.x (Security 6) | Spring Boot 4.x (Security 7) |
| :--- | :--- | :--- |
| **Filter Pipeline Overhead** | Hand-rolled `JwtAuthenticationFilter` manually extracting tokens and managing exception dispatch. | **Declarative Resource Server Standard**: Uses built-in reactive/stateless JWT decoders with zero custom filter boilerplate. |
| **Asymmetric Key Rotation (JWKS)** | Required custom Nimbus / JJWT cache refresh logic or manual cron timers. | **Native JWKS Auto-Cache & Rotation**: Native support for OpenID Connect JSON Web Key Sets with automatic rollover. |
| **Authentication Token Footprint** | ThreadLocal `UsernamePasswordAuthenticationToken` instances. | **Scoped JWT Principals**: Immutable token context propagated cleanly across Virtual Threads without leaks. |

---

## 6. Primary Sources & Further Reading

- [RFC 7519: JSON Web Token (JWT) Specification](https://datatracker.ietf.org/doc/html/rfc7519) — Claims, encoding, and signature format standards.
- [JJWT (Java JWT) Library Documentation](https://github.com/jwtk/jjwt) — Modern Java fluent API for HMAC and RSA signing.
- [OWASP REST Security Cheat Sheet: JWT](https://cheatsheetseries.owasp.org/cheatsheets/JSON_Web_Token_for_Java_Cheat_Sheet.html) — Secure key length, algorithm hardening, and replay mitigation.

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: Why must the secret key used for HMAC-SHA256 (`HS256`) be at least 256 bits (32 bytes) long?"
    **Answer**: HMAC-SHA256 requires a key length equal to or greater than its output block size (256 bits) to prevent brute-force dictionary attacks against the digital signature.

??? question "Question 2: Why should `JwtAuthenticationFilter` extend `OncePerRequestFilter` instead of implementing `Filter` directly?"
    **Answer**: `OncePerRequestFilter` guarantees that the filter is executed exactly once per request dispatch within a single request thread, preventing duplicate filter invocations during internal Servlet forward or error dispatches.

??? question "Question 3: How does the Access Token + Refresh Token pattern solve the problem of token revocation without sacrificing statelessness on every request?"
    **Answer**: Access tokens have short lifespans (e.g., 15 mins) and are validated statelessly on resource APIs without hitting databases; only when refreshing tokens (e.g., every 15 mins) is the database or Redis checked for revocation.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0024: Password Hashing & Sessions**](0024-password-hashing-bcrypt-argon2-sessions.md) | [**All Lessons**](index.md) | [➡️ **0026: Role & Permission Access Control**](0026-role-and-permission-based-access-control-rbac.md) |
