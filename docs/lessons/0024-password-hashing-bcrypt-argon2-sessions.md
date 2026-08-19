---
icon: lucide/key-round
---

# 0024: Password hashing (BCrypt, Argon2) and user session management

Storing user credentials and managing stateful user sessions are the two most security-sensitive tasks in any backend architecture. A simple flaw, such as using fast hashing algorithms like SHA-256 or failing to rotate session IDs on authentication, exposes user data to GPU rainbow table cracking and session fixation attacks.

In this lesson, you will master cryptographic password hashing using **BCrypt** and **Argon2id**, understand Spring Security's `DelegatingPasswordEncoder`, configure stateful session fixation protections, and implement concurrent session controls.

---

## 1. Fast hashes vs adaptive memory-hard hashes

Fast cryptographic hashes (e.g., MD5, SHA-1, SHA-256) were designed for message integrity, calculating millions of hashes per second. This speed makes them fatally vulnerable to brute-force attacks using modern GPUs and ASICs.

Password hashing algorithms must be **slow, salted, and computationally expensive**:

``` mermaid
flowchart TD
    subgraph FastHash["❌ Fast Hashes (MD5 / SHA-256)"]
        P1["Raw Password"] --> SHA["SHA-256 Engine"]
        SHA --> H1["Fast Hash<br/><i>(10,000,000,000 / sec on GPU)</i>"]
    end

    subgraph AdaptiveHash["✅ Adaptive Hashes (BCrypt / Argon2)"]
        P2["Raw Password"] --> Salt["Random 128-bit Salt"]
        Salt --> Engine["Adaptive Cost Engine<br/><i>(Work Factor / Memory Hardness)</i>"]
        Engine --> H2["Slow Hash<br/><i>(~100-300ms per attempt)</i>"]
    end

    FastHash ~~~ AdaptiveHash
```

### Comparison of modern password encoders

| Algorithm | Mechanism | Memory Hardness | Winner of Password Hashing Competition | Enterprise Recommendation |
| :--- | :--- | :---: | :---: | :--- |
| **BCrypt** | Blowfish cipher with adaptive logarithmic cost (rounds $2^{10}$ to $2^{14}$). | ❌ CPU bound | No | **Spring Boot Default / Industry Standard** |
| **Argon2id** | Hybrid memory-hard algorithm resistant to GPU, FPGA, and ASIC attacks. | ✅ RAM bound (e.g., 64MB per hash) | **Yes (PHC Winner)** | **Highest Security Level (OWASP #1)** |
| **PBKDF2** | Repeated HMAC iterations ($>600,000$ rounds). | ❌ CPU bound | No | Legacy FIPS compliance |

---

## 2. Spring security `DelegatingPasswordEncoder`

Spring Security does not hardcode a single algorithm. Instead, it uses `DelegatingPasswordEncoder` to prefix encoded hashes with an algorithm identifier (e.g., `{bcrypt}`, `{argon2}`). This allows seamless password upgrade migrations without breaking existing user accounts.

``` mermaid
flowchart TD
    Raw["Raw Input: 'P@ssw0rd123'"] --> Matcher["DelegatingPasswordEncoder.matches()"]
    DBHash["DB Hash: '{argon2}$argon2id$v=19$m=16384...'"] --> Matcher
    
    Matcher --> Extract["Extract Prefix: 'argon2'"]
    Extract --> Delegate["Delegate to Argon2PasswordEncoder"]
    Delegate --> Verify["Cryptographic Verification"]
    Verify -->|Matches| Result["Authentication Success ✅"]
    Verify -->|Mismatch| Fail["BadCredentialsException ❌"]
```

### Configuring modern password encoders
```java
package com.example.security.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.crypto.argon2.Argon2PasswordEncoder;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.DelegatingPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.HashMap;
import java.util.Map;

@Configuration
public class PasswordEncoderConfig {

    @Bean
    public PasswordEncoder passwordEncoder() {
        // Default Spring factory (supports {bcrypt}, {argon2}, {pbkdf2}, etc.)
        // return PasswordEncoderFactories.createDelegatingPasswordEncoder();

        // Custom enterprise configuration: Default to Argon2id with backward compatibility
        String defaultEncodingId = "argon2";
        Map<String, PasswordEncoder> encoders = new HashMap<>();
        
        // Argon2id parameters: saltLength=16, hashLength=32, parallelism=1, memory=65536KB (64MB), iterations=3
        encoders.put("argon2", new Argon2PasswordEncoder(16, 32, 1, 65536, 3));
        encoders.put("bcrypt", new BCryptPasswordEncoder(12));

        DelegatingPasswordEncoder delegatingPasswordEncoder = 
            new DelegatingPasswordEncoder(defaultEncodingId, encoders);
        
        // Fallback if legacy password has no prefix
        delegatingPasswordEncoder.setDefaultPasswordEncoderForMatches(new BCryptPasswordEncoder(10));
        
        return delegatingPasswordEncoder;
    }
}
```

---

## 3. Session management session fixation protection

In stateful web applications, the server tracks authenticated sessions via a session cookie (`JSESSIONID`).

### The session fixation attack defense
In a **Session Fixation** attack, an attacker forces an anonymous user to browse with an attacker-known `JSESSIONID`. Once the victim logs in, if the application does not change the session ID, the attacker can hijack the authenticated session.

``` mermaid
sequenceDiagram
    autonumber
    actor Attacker as Attacker
    actor Victim as Victim
    participant App as Spring Boot App

    Attacker->>App: 1. Anonymous Visit -> Obtains JSESSIONID=XYZ
    Attacker->>Victim: 2. Sends phishing link with JSESSIONID=XYZ
    Victim->>App: 3. Logs in with JSESSIONID=XYZ credentials
    
    rect rgb(240, 255, 240)
        Note over App: Spring Security Session Fixation Defense:
        App->>App: Creates NEW session ID=ABC & migrates session attributes
        App-->>Victim: Returns Set-Cookie: JSESSIONID=ABC
    end
    
    Attacker->>App: 4. Attempts request with JSESSIONID=XYZ
    App-->>Attacker: 401 Unauthorized / Anonymous (XYZ invalidated!)
```

### Spring security session fixation strategies
- `migrateSession()` *(Default)*: Creates a new HTTP session, copies all existing session attributes to the new session, and invalidates the old one.
- `changeSessionId()`: uses Servlet 3.1 `HttpServletRequest.changeSessionId()` to update the ID without touching session attributes.
- `newSession()`: Creates a new clean session without copying any previous attributes.
- `none()`: Disables fixation protection (strongly discouraged).

---

## 4. Concurrent session control maximum sessions

To prevent account sharing or credential abuse, Spring Security allows capping the number of active sessions per user account:

```java
package com.example.security.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.session.SessionRegistry;
import org.springframework.security.core.session.SessionRegistryImpl;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.session.HttpSessionEventPublisher;

@Configuration
public class StatefulSecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/login", "/public/**").permitAll()
                .anyRequest().authenticated()
            )
            .formLogin(form -> form
                .loginPage("/login")
                .defaultSuccessUrl("/dashboard", true)
                .permitAll()
            )
            .sessionManagement(session -> session
                // 1. Session Fixation Protection
                .sessionFixation().migrateSession()
                
                // 2. Concurrent Session Control: Max 1 active session per user
                .maximumSessions(1)
                // If maxSessionsPreventsLogin is true, second login is rejected.
                // If false (default), second login succeeds and kicks out first session.
                .maxSessionsPreventsLogin(false)
                .expiredUrl("/login?expired=true")
                .sessionRegistry(sessionRegistry())
            );

        return http.build();
    }

    @Bean
    public SessionRegistry sessionRegistry() {
        return new SessionRegistryImpl();
    }

    // Required for Spring Security to track session lifecycle events (creation / destruction)
    @Bean
    public HttpSessionEventPublisher httpSessionEventPublisher() {
        return new HttpSessionEventPublisher();
    }
}
```

---

## 5. Csrf (cross-site request forgery) protection

CSRF attacks trick an authenticated user's browser into executing unwanted state-changing actions (e.g., POST `/transfer-funds`) on a trusted site where the user holds an active cookie.

``` mermaid
sequenceDiagram
    autonumber
    actor User as User Browser (Logged In)
    participant Bank as Banking App (Stateful Session)
    actor Evil as Malicious Site (evil.com)

    User->>Bank: GET /dashboard (Receives JSESSIONID + XSRF-TOKEN cookie)
    User->>Evil: Browses malicious site in another tab
    Evil->>Bank: Hidden form POST /api/transfer (Browser auto-attaches JSESSIONID)
    
    alt CSRF Enabled (Synchronizer Token)
        Bank->>Bank: Validates X-XSRF-TOKEN header vs Cookie
        Note over Bank: Header is missing / mismatch!
        Bank-->>Evil: 403 Forbidden (Attack Prevented 🛡️)
    else CSRF Disabled
        Bank->>Bank: Trust cookies blindly
        Bank-->>Evil: 200 OK (Funds stolen!)
    end
```

### When to enable vs disable csrf
- **Enable CSRF**: For any application using browser cookies (`JSESSIONID`, session cookies) for authentication (e.g., Thymeleaf, JSP, or traditional cookie-based SPAs).
- **Disable CSRF (`csrf.disable()`)**: For stateless REST APIs using `Authorization: Bearer <JWT>` where browsers do not automatically send tokens on cross-origin requests.

---

## 6. Spring Boot 3 vs Spring Boot 4: Password identity evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Security 6)"]
        DefaultBCrypt["BCrypt Default in PasswordEncoderFactories"]
        ManualArgonConfig["Manual Argon2PasswordEncoder Bean Wiring"]
        ThirdPartyWebAuthn["Third-Party WebAuthn Libraries for Passkeys"]
    end

    subgraph SB4["Spring Boot 4.x (Security 7)"]
        ArgonDefault["Argon2id Optimized Default Parameter Sets"]
        NativePasskeys["Native Passkey / WebAuthn Starter (FIDO2)"]
        ScopedSession["Loom-Safe Stateless Session Replicators"]
    end

    SB3 ==>|Passwordless Modernization| SB4
```

### Key differences and configuration comparison

| Identity & Storage Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Default Password Algorithm** | `PasswordEncoderFactories` defaulted to `{bcrypt}` rounds=10. | **Argon2id Memory-Hard Default**: Default work parameters scaled for modern CPU/RAM baselines. |
| **Passkey / FIDO2 Support** | Required manual integration with external libraries (e.g. Yubico `webauthn-server-core`). | **Native WebAuthn Auto-Configuration**: Native support for biometric / hardware security key logins. |
| **Session Fixation Engine** | Standard `HttpSession.changeSessionId()` via Servlet 3.1. | **Virtual-Thread Optimized Session Tokens**: Lightweight memory footprint under millions of concurrent connections. |

---

## 7. Primary sources and further reading

- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), Work factors, salt sizes, and memory parameters.
- [Spring Security Password Storage Documentation](https://docs.spring.io/spring-security/reference/features/authentication/password-storage.html), `DelegatingPasswordEncoder` and migration patterns.
- [Spring Security Session Management Guide](https://docs.spring.io/spring-security/reference/servlet/authentication/session-management.html), Concurrent sessions, fixation defense, and session registry.

---

## 8. Knowledge check and practice

??? question "Question 1: Why is SHA-256 unsuitable for storing user passwords in modern web applications?"
    **Answer**: SHA-256 is designed to be extremely fast for data integrity, enabling modern GPUs and ASICs to compute billions of hashes per second and rapidly crack passwords via brute-force and rainbow tables.

??? question "Question 2: What is the primary purpose of the algorithm prefix (e.g., `{bcrypt}`, `{argon2}`) in Spring Security's `DelegatingPasswordEncoder`?"
    **Answer**: The prefix identifies which specific cryptographic encoder to use for verifying an existing hash, allowing seamless migration and upgrades to stronger algorithms without breaking existing user accounts.

??? question "Question 3: How does the `migrateSession()` session fixation defense prevent an attacker from hijacking a victim's session?"
    **Answer**: Upon successful authentication, Spring Security invalidates the existing HTTP session ID, generates a brand new session ID, and migrates existing attributes so the attacker's pre-known ID is rendered useless.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0023: Spring Security 6 Architecture**](0023-spring-security-6-architecture-filter-chains.md) | [**All Lessons**](index.md) | [ **0025: Stateless JWT Authentication**](0025-stateless-jwt-authentication-filter.md) |
