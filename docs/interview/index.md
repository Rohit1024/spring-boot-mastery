---
icon: lucide/help-circle
---

# Senior Spring Boot & System Design Interview Questions

Curated, high-signal technical and architectural interview questions for Senior Java / Spring Backend and Distributed Systems Engineering roles.

---

## 🏛️ Core Spring & Framework Internals
- **IoC & Bean Lifecycle**: Explain what happens under the hood when `ApplicationContext` initializes a `@Service` bean with `@Transactional`.
- **Proxy Mechanisms**: How does Spring decide between JDK Dynamic Proxies vs CGLIB, and why does `@Transactional` fail on self-invocation?
- **Auto-Configuration**: How does `@ConditionalOnMissingBean` and `@AutoConfiguration` work during startup?

---

## 🌐 Spring MVC, REST & API Design
- **DispatcherServlet Pipeline**: Walk through the step-by-step dispatch process when an incoming HTTP POST request hits `DispatcherServlet` through to `HandlerMapping`, `HandlerAdapter`, `HttpMessageConverter`, and `HandlerInterceptor`.
- **Filters vs Interceptors**: Contrast a Servlet `OncePerRequestFilter` with a Spring `HandlerInterceptor`. In what phase of the pipeline does each execute, and which has access to the target `HandlerMethod` metadata?
- **Idempotency in REST**: Why is `PUT` idempotent while `POST` is not? How do you design idempotent `POST` endpoints in distributed payment systems?
- **RFC 7807 / RFC 9457 `ProblemDetail`**: How does Spring Boot 3.x handle API error responses compared to legacy `@ControllerAdvice` wrappers?
- **Entity vs DTO Anti-Pattern**: Why is returning JPA Entities directly from a `@RestController` considered a critical security vulnerability and architectural anti-pattern?
- **Strategy Pattern with Spring IoC**: How do you implement dynamic algorithm/payment provider selection using Spring's automatic `Map<String, StrategyInterface>` injection?

---

## 💾 Persistence, JPA, Transactions & Caching
- **Hibernate Dirty Checking**: Explain the exact snapshot comparison mechanism Hibernate uses during `flush()` and why calling `repository.save()` on a managed entity is redundant.
- **Entity Lifecycle States**: Contrast `TRANSIENT`, `MANAGED`, `DETACHED`, and `REMOVED`. What happens if you call `setBalance()` on a detached entity?
- **N+1 Problem & Mitigation**: Walk through the N+1 query problem, why JPA's default `FetchType.EAGER` on `@ManyToOne` is dangerous, and compare `JOIN FETCH`, `@EntityGraph`, `@BatchSize`, and DTO projections.
- **Transaction Propagation**: Compare `REQUIRED`, `REQUIRES_NEW`, and `NESTED`. Walk through a scenario where audit logs must persist even if the parent business transaction fails and rolls back.
- **Proxy Self-Invocation**: Why does `@Transactional` fail to start a transaction when called from another method within the same bean, and how does Spring's CGLIB proxy architecture cause this?
- **Rollback Rules**: Which exception types trigger an automatic transaction rollback by default in Spring, and how do you ensure checked exceptions roll back?
- **Isolation Levels & Anomalies**: Compare `READ_COMMITTED` vs `REPEATABLE_READ` vs `SERIALIZABLE` in terms of Dirty Reads, Non-Repeatable Reads, and Phantom Reads.
- **`Page<T>` vs `Slice<T>`**: Why does `Page<T>` cause serious performance degradation on large tables, and how does `Slice<T>` avoid the `COUNT(*)` query?
- **Polyglot & Multi-DataSource**: How do you configure multiple `EntityManagerFactory` and `PlatformTransactionManager` beans to connect to PostgreSQL and MySQL in the same Spring Boot application?
- **Hibernate Envers & Soft Deletes**: How does Envers maintain historical audit logs via shadow tables (`_AUD`), and how does `@SQLRestriction` implement modern soft deletes in Hibernate 6.x?
- **Cache Stampede**: How do you prevent cache breakdown / stampede when using Redis caching with high concurrency?

---

## 🛠️ Observability, Actuator, Logging & API Documentation
- **Kubernetes Liveness vs Readiness**: What is the difference between `/actuator/health/liveness` and `/actuator/health/readiness`? What action does Kubernetes take when each returns `DOWN`?
- **Micrometer Metrics**: Contrast a `Counter`, `Timer`, and `Gauge`. How do you publish pre-calculated percentile SLAs (`p50`, `p95`, `p99`) to Prometheus?
- **MDC & Thread Pools**: Why is clearing SLF4J MDC in a `finally` block mandatory in Tomcat/Jetty web servers, and how do you propagate MDC context into `@Async` worker threads?
- **Dynamic Log Level Adjustments**: How do you change a production logger from `INFO` to `DEBUG` in real time without restarting the application container?
- **Spring Boot DevTools Classloaders**: Explain the Two-ClassLoader architecture (Base vs Restart) and how it achieves sub-second local restarts.
- **OpenAPI / Swagger UI Security**: How do you configure SpringDoc to require and inject a JWT Bearer token across protected REST API endpoints?

---

## 🔒 Spring Security 6, JWT, OAuth2 & Identity
- **Filter Chain Delegation**: Walk through the lifecycle of an incoming HTTP request starting at Tomcat's `DelegatingFilterProxy` through `FilterChainProxy`, `SecurityFilterChain`, `AuthenticationManager`, and `AuthorizationFilter`.
- **Spring Security 6 Breaking Changes**: Why was `WebSecurityConfigurerAdapter` removed, and how does modern component-based security configure `SecurityFilterChain` beans using lambda DSLs?
- **Password Hashing Algorithms**: Why are MD5 and SHA-256 considered catastrophic vulnerabilities for password storage, and how do BCrypt and Argon2id implement adaptive cost factors and memory-hardness against GPU/ASIC cracking?
- **`DelegatingPasswordEncoder` Prefixing**: How does Spring Security use prefixes like `{bcrypt}` and `{argon2}` to support seamless zero-downtime password hashing migrations?
- **Session Fixation Defense**: Explain how an attacker conducts a session fixation attack and how `migrateSession()` mitigates this during authentication.
- **JWT Architecture & Statelessness**: Break down the structure of a JWT (Header, Payload, Signature). Why is HMAC-SHA256 symmetric while RS256 is asymmetric, and how do you implement Access Token + Refresh Token rotation?
- **JWT Filter Exception Handling**: Why does `@RestControllerAdvice` fail to intercept `ExpiredJwtException` thrown inside `JwtAuthenticationFilter`, and how does delegating to `HandlerExceptionResolver` resolve this?
- **Roles vs Authorities & Prefixing**: Contrast `hasRole('ADMIN')` with `hasAuthority('ADMIN')` in Spring Security. Why does omitting the `ROLE_` prefix cause silent 403 Forbidden errors?
- **Method Security Mechanics**: How does `@EnableMethodSecurity` use Spring AOP CGLIB proxies to evaluate `@PreAuthorize` and `@PostAuthorize` expressions before/after method invocation?
- **OAuth 2.0 vs OpenID Connect (OIDC)**: Contrast delegated authorization (`access_token`) with authentication identity (`id_token`). Walk through the Authorization Code Flow with PKCE and explain how a backend bridges social login with stateless JWT issuance for SPA clients.

---

## 📦 Packaging, Containerization (Jib), Multi-Cloud Registries & GraalVM Native
- **Fat JAR vs Layered JAR**: Why does deploying a monolithic Fat JAR inside a Docker container destroy Docker layer caching? Explain how `jarmode=layertools` extracts the archive into four discrete layers (`dependencies`, `spring-boot-loader`, `snapshot-dependencies`, `application`).
- **Google Jib Architecture**: How does Google Jib construct OCI-compliant container images without a Docker daemon or Dockerfile? What are the security benefits in Kubernetes-based CI/CD pipelines?
- **Jib Layer Caching Performance**: How does Jib arrange build outputs so that a one-line Java code change only invalidates and pushes a ~200KB classes layer instead of the entire application footprint?
- **Multi-Cloud Credential Helpers**: How does Jib authenticate with Google Cloud Artifact Registry (`docker-credential-gcr`), AWS ECR (`docker-credential-ecr-login`), and Azure ACR (`docker-credential-acr-env`) without storing static secrets in build files?
- **Container Memory Ergonomics**: Why is `-XX:MaxRAMPercentage=75.0` strongly preferred over fixed `-Xmx` values when running Java containers in Kubernetes?
- **GraalVM Closed-World Assumption**: What is the Closed-World Assumption in GraalVM Ahead-Of-Time (AOT) compilation? Why does dead-code elimination break un-hinted runtime reflection and dynamic proxies?
- **Spring AOT Processing Engine**: How does Spring Boot 3+ evaluate bean definitions and `@Conditional` annotations at build time to generate static initializers and reflection reachability metadata?
- **Custom `RuntimeHintsRegistrar`**: When and how do you implement `RuntimeHintsRegistrar` or `@RegisterReflectionForBinding` to register third-party DTOs and resources for GraalVM native compilation?
- **GraalVM + Jib Hybrid Containerization**: Explain how to package a compiled GraalVM native machine executable into a microscopic (~45MB) `gcr.io/distroless/base-debian12` container using Jib's `extraDirectories` and entrypoint configuration.
- **Troubleshooting Native Container Failures**: Why does running a dynamically linked GraalVM native binary on a `distroless/static-debian12` base image trigger `exec user process caused: no such file or directory`, and how do you resolve it?

---

## ⚡ Distributed Systems & Microservices
- **SAGA vs 2PC**: Why is Two-Phase Commit anti-pattern in microservices, and how does SAGA choreography handle rollbacks via compensating transactions?
- **Transactional Outbox**: How do you guarantee zero-loss message publishing between PostgreSQL and Apache Kafka?
- **Rate Limiting**: Contrast Token Bucket vs Sliding Window Log implementation using Redis Lua scripts.

