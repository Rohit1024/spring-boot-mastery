---
icon: lucide/globe
---

# 0027: Third-party authentication with Google OAuth2 and OpenID Connect (OIDC)

Forcing users to create and remember yet another password increases registration friction and burdens systems with credential storage compliance. **OAuth 2.0** and **OpenID Connect (OIDC 1.0)** allow applications to securely delegate authentication to trusted identity providers (IdPs) like Google, GitHub, and Okta.

In this lesson, you will master the OAuth 2.0 Authorization Code Flow with PKCE, configure Spring Security 6's OAuth2 Client, implement a custom `DefaultOAuth2UserService` to auto-provision users in a local PostgreSQL database, and bridge social logins with stateless JWT issuance for single-page applications.

---

## 1. Oauth 20 vs openid connect (OIDC)

Understanding the distinction between OAuth 2.0 and OIDC is essential:

- **OAuth 2.0 (Delegated Authorization)**: Issues an **`access_token`** granting an application permission to access protected APIs (e.g., read Google Calendar) on behalf of a user. It does not standardize user identity.
- **OpenID Connect (Identity Layer)**: An identity layer on top of OAuth 2.0. In addition to the access token, the IdP returns an **`id_token`** (a signed JWT containing verified identity claims like `sub`, `email`, `name`, `picture`).

``` mermaid
flowchart TD
    subgraph OAuth2["OAuth 2.0 (Authorization)"]
        AT["🔑 access_token<br/><i>(Opaque or JWT)</i><br/>Used for API requests"]
    end

    subgraph OIDC["OpenID Connect 1.0 (Authentication)"]
        ID["🪪 id_token<br/><i>(Signed JWT)</i><br/>Verified Identity Claims"]
        UI["👤 UserInfo Endpoint<br/>Profile Metadata"]
    end

    OAuth2 --- OIDC
```

---

## 2. Authorization code flow with pkce sequence

The **Authorization Code Flow with Proof Key for Code Exchange (PKCE)** is the gold standard for secure social login:

``` mermaid
sequenceDiagram
    autonumber
    actor User as User Browser
    participant App as Spring Boot Backend (:8080)
    participant Google as Google Identity Provider (accounts.google.com)
    participant DB as Local PostgreSQL DB

    User->>App: 1. Click "Login with Google" (/oauth2/authorization/google)
    App-->>User: 302 Redirect to Google Auth URL (with client_id, redirect_uri, scope=openid email)
    User->>Google: 2. Authenticates & Grants Consent
    Google-->>User: 302 Redirect to App Callback with Authorization `code`
    
    User->>App: 3. GET /login/oauth2/code/google?code=AUTH_CODE
    App->>Google: 4. POST /token (Exchanges code + client_secret for id_token & access_token)
    Google-->>App: Returns id_token (JWT) + access_token
    
    App->>App: 5. Validates id_token signature & claims
    App->>DB: 6. CustomOAuth2UserService: Find or Create User Entity
    DB-->>App: Persisted User Record (roles assigned)
    App-->>User: 7. Sets Session Cookie or Redirects to SPA with JWT Token
```

---

## 3. Configuring Spring Boot OAuth2 client

### Dependencies (`pomxml`)
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-oauth2-client</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
```

### Configuration (`applicationyml`)
```yaml
spring:
  security:
    oauth2:
      client:
        registration:
          google:
            client-id: ${GOOGLE_CLIENT_ID}
            client-secret: ${GOOGLE_CLIENT_SECRET}
            scope:
              - openid
              - profile
              - email
            redirect-uri: "{baseUrl}/login/oauth2/code/{registrationId}"
```

---

## 4. Auto-provisioning users in database on social login

When a user signs in via Google for the first time, your application must persist a corresponding local user record in PostgreSQL to track application-specific relationships (e.g., orders, roles, subscriptions).

### `CustomOAuth2UserService.java`
```java
package com.example.security.oauth2;

import com.example.security.entity.AuthProvider;
import com.example.security.entity.UserEntity;
import com.example.security.repository.UserRepository;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.client.userinfo.DefaultOAuth2UserService;
import org.springframework.security.oauth2.client.userinfo.OAuth2UserRequest;
import org.springframework.security.oauth2.core.OAuth2AuthenticationException;
import org.springframework.security.oauth2.core.user.DefaultOAuth2User;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Collections;
import java.util.Map;

@Service
public class CustomOAuth2UserService extends DefaultOAuth2UserService {

    private final UserRepository userRepository;

    public CustomOAuth2UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @Override
    @Transactional
    public OAuth2User loadUser(OAuth2UserRequest userRequest) throws OAuth2AuthenticationException {
        // 1. Fetch user attributes from Google UserInfo endpoint
        OAuth2User oAuth2User = super.loadUser(userRequest);
        Map<String, Object> attributes = oAuth2User.getAttributes();

        String email = (String) attributes.get("email");
        String name = (String) attributes.get("name");
        String googleId = (String) attributes.get("sub");

        // 2. Find existing user or auto-provision new record in PostgreSQL
        UserEntity user = userRepository.findByEmail(email)
                .map(existingUser -> updateExistingUser(existingUser, name))
                .orElseGet(() -> registerNewOAuthUser(email, name, googleId));

        // 3. Return authenticated principal with assigned authorities
        return new DefaultOAuth2User(
                Collections.singleton(new SimpleGrantedAuthority("ROLE_" + user.getRole())),
                attributes,
                "email" // Name attribute key
        );
    }

    private UserEntity registerNewOAuthUser(String email, String name, String providerId) {
        UserEntity newUser = UserEntity.builder()
                .email(email)
                .fullName(name)
                .provider(AuthProvider.GOOGLE)
                .providerId(providerId)
                .role("USER")
                .enabled(true)
                .build();
        return userRepository.save(newUser);
    }

    private UserEntity updateExistingUser(UserEntity existingUser, String name) {
        existingUser.setFullName(name);
        return userRepository.save(existingUser);
    }
}
```

---

## 5. Bridging OAuth2 social login to stateless spa / mobile JWT

For Single-Page Apps (React/Vue/Angular) or Mobile Apps, you do not want stateful cookies upon OAuth2 login completion. Instead, use a custom `AuthenticationSuccessHandler` to generate a JWT and redirect to the frontend:

### `OAuth2AuthenticationSuccessHandler.java`
```java
package com.example.security.oauth2;

import com.example.security.jwt.JwtService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.oauth2.core.user.OAuth2User;
import org.springframework.security.web.authentication.SimpleUrlAuthenticationSuccessHandler;
import org.springframework.stereotype.Component;
import org.springframework.web.util.UriComponentsBuilder;

import java.io.IOException;

@Component
public class OAuth2AuthenticationSuccessHandler extends SimpleUrlAuthenticationSuccessHandler {

    private final JwtService jwtService;
    private final UserDetailsService userDetailsService;
    
    @Value("${application.oauth2.authorized-redirect-uri:http://localhost:3000/oauth2/redirect}")
    private String redirectUri;

    public OAuth2AuthenticationSuccessHandler(JwtService jwtService, UserDetailsService userDetailsService) {
        this.jwtService = jwtService;
        this.userDetailsService = userDetailsService;
    }

    @Override
    public void onAuthenticationSuccess(HttpServletRequest request, HttpServletResponse response, Authentication authentication) throws IOException {
        OAuth2User oAuth2User = (OAuth2User) authentication.getPrincipal();
        String email = oAuth2User.getAttribute("email");

        UserDetails userDetails = userDetailsService.loadUserByUsername(email);
        String token = jwtService.generateToken(userDetails);

        // Redirect to Frontend SPA URL with JWT as query parameter (or set secure HttpOnly cookie)
        String targetUrl = UriComponentsBuilder.fromUriString(redirectUri)
                .queryParam("token", token)
                .build().toUriString();

        getRedirectStrategy().sendRedirect(request, response, targetUrl);
    }
}
```

### Wiring into `SecurityConfig.java`
```java
@Bean
public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
    http
        .csrf(AbstractHttpConfigurer::disable)
        .authorizeHttpRequests(auth -> auth
            .requestMatchers("/", "/login/**", "/oauth2/**").permitAll()
            .anyRequest().authenticated()
        )
        .oauth2Login(oauth2 -> oauth2
            .userInfoEndpoint(userInfo -> userInfo.userService(customOAuth2UserService))
            .successHandler(oAuth2AuthenticationSuccessHandler)
        );

    return http.build();
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4: OAuth2 OIDC identity evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (OAuth2 Client)"]
        ManualTokenBridge["Manual SuccessHandler JWT URL Redirect"]
        FrontChannelLogout["Front-Channel Browser Redirect Logout"]
        ExplicitProviders["Discrete Provider YAML Blocks"]
    end

    subgraph SB4["Spring Boot 4.x (Identity Federation)"]
        NativeSpaBridge["Built-in Native SPA Token Bridge"]
        BackChannelLogout["OIDC Back-Channel Logout 1.0 Standard"]
        PasskeyFederation["Unified Social & Passkey Federation Engine"]
    end

    SB3 ==>|Identity Federation Modernization| SB4
```

### Key differences and configuration comparison

| OAuth2 & OIDC Capability | Spring Boot 3.x (Security 6) | Spring Boot 4.x (Security 7) |
| :--- | :--- | :--- |
| **SPA Token Exchange** | Required custom `OAuth2AuthenticationSuccessHandler` redirecting with query tokens. | **Native SPA Token Bridge**: Auto-provisions and returns secure HttpOnly tokens to configured origins. |
| **OIDC Single Sign-Out** | Limited to front-channel HTTP 302 browser redirects. | **OIDC Back-Channel Logout 1.0**: IdP sends server-to-server logout tokens to invalidate sessions instantly across fleet. |
| **Identity Provider Federation** | Strict separation between standard OAuth2 login and local password accounts. | **Unified Social + WebAuthn Identity**: Single declarative interface merging Google, GitHub, and Passkeys. |

---

## 7. Primary sources and further reading

- [Spring Security 6 OAuth 2.0 Client Documentation](https://docs.spring.io/spring-security/reference/servlet/oauth2/client/index.html), Client registrations, authorization code requests, and token exchange.
- [RFC 7636: Proof Key for Code Exchange (PKCE)](https://datatracker.ietf.org/doc/html/rfc7636), Preventing authorization code interception attacks.
- [OpenID Connect Core 1.0 Specification](https://openid.net/specs/openid-connect-core-1_0.html), Standard claims, ID tokens, and validation rules.

---

## 8. Knowledge check and practice

??? question "Question 1: What is the key functional difference between OAuth 2.0 and OpenID Connect (OIDC 1.0)?"
    **Answer**: OAuth 2.0 is a delegated authorization framework that issues access tokens for API calls, whereas OIDC 1.0 is an authentication layer built on top of OAuth 2.0 that provides identity tokens (`id_token`) and user profile claims.

??? question "Question 2: Why is PKCE (Proof Key for Code Exchange) recommended even for server-side confidential clients in OAuth 2.0?"
    **Answer**: PKCE dynamically binds the authorization code request to the token exchange request via cryptographic code verifiers, preventing authorization code injection and interception attacks.

??? question "Question 3: In an SPA architecture, why should the backend OAuth2 success handler redirect with a JWT rather than relying on the JSESSIONID cookie created during the Google callback?"
    **Answer**: To preserve a purely stateless API architecture on subsequent REST requests, enabling client apps to store tokens and query microservices horizontally without session affinity or sticky sessions.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0026: Role & Permission Access Control**](0026-role-and-permission-based-access-control-rbac.md) | [**All Lessons**](index.md) | [ **0028: Packaging Paradigms (JAR & Docker)**](0028-packaging-paradigms-jar-docker-layering.md) |

🎉 **Congratulations on completing Module 5: Spring Security 6, OAuth2 & Identity!**
