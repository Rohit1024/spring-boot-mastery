# Spring Boot & Distributed Architecture Glossary

Canonical definitions for key concepts across our lessons.

## Spring Framework Core

**IoC (Inversion of Control)**:
An architectural principle where the framework manages object creation and dependency binding rather than objects instantiating their own dependencies.

**Spring Bean**:
A Java object whose lifecycle (instantiation, configuration, wiring, and destruction) is fully managed by the Spring IoC container (`ApplicationContext`).

**Dependency Injection (DI)**:
A specialized form of IoC where dependencies are passed into a dependent object (via constructor, setter, or field) rather than created internally.

**Auto-Configuration**:
Spring Boot's mechanism of inspecting the classpath, active profiles, and defined beans to automatically instantiate and configure infrastructure beans with sensible defaults.

**AOP (Aspect-Oriented Programming)**:
A paradigm that modularizes cross-cutting concerns (such as logging, transaction management, or metrics) by intercepting method executions using pointcuts and advice.

## Web MVC & REST APIs

**DispatcherServlet**:
The central Front Controller servlet in Spring MVC that coordinates request dispatching, handler mapping, method execution, argument resolution, and response rendering.

**HandlerMapping**:
An interface implemented by objects that define a mapping between incoming HTTP requests and handler objects (controllers/methods).

**HttpMessageConverter**:
A strategy interface that converts HTTP request bodies to Java objects (deserialization) and Java objects to HTTP response bodies (serialization, e.g. Jackson for JSON).

**HandlerInterceptor**:
An interceptor interface in Spring MVC allowing pre-processing (`preHandle`), post-processing (`postHandle`), and complete request cleanup (`afterCompletion`) around controller executions.

**DTO (Data Transfer Object)**:
An object that carries data between processes or application layers without containing business logic, preventing entity exposure and mass-assignment vulnerabilities.

**ProblemDetail (RFC 9457 / RFC 7807)**:
An IETF standard format for HTTP API error responses containing standardized fields (`type`, `title`, `status`, `detail`, `instance`).

**Strategy Pattern**:
A behavioral design pattern that enables selecting an algorithm's implementation dynamically at runtime, natively implemented in Spring via `Map<String, T>` autowiring.

## Data & Persistence

**Hibernate ORM**:
An Object-Relational Mapping framework that translates between Java objects (Entities) and relational database tables.

**Spring Data JPA**:
An abstraction layer built on top of JPA/Hibernate that generates repository implementations and queries at runtime based on interface method signatures.

**Persistence Context**:
A first-level in-memory cache and staging environment managed by an `EntityManager` where entity lifecycle states and dirty checks are tracked.

**Dirty Checking**:
Hibernate's automatic mechanism of comparing managed entity states against their initial snapshot during transaction flush to issue minimal SQL `UPDATE` statements without manual save calls.

**N+1 Query Problem**:
A performance anti-pattern where 1 query fetches $N$ parent records, and subsequent iteration triggers $N$ additional queries to fetch lazily loaded children.

**JOIN FETCH**:
A JPQL query clause that instructs Hibernate to initialize associations eagerly in a single SQL `JOIN` query, eliminating N+1 queries.

**Transaction Propagation**:
A Spring configuration specifying how transactional boundaries behave when one transactional method invokes another (e.g. `REQUIRED`, `REQUIRES_NEW`, `NESTED`).

**Hibernate Envers**:
A Hibernate extension that automatically maintains historical revision logs in shadow `_AUD` tables whenever audited entities are inserted, updated, or deleted.

**R2DBC (Reactive Relational Database Connectivity)**:
A non-blocking database driver specification designed for reactive streams, replacing blocking JDBC calls.


## Observability, Tooling & Logging

**Spring Boot Actuator**:
A production-ready feature suite that exposes monitoring, health probes, metrics, and application metadata over HTTP/JMX endpoints.

**Micrometer**:
A vendor-neutral application metrics facade for the JVM that exports dimensional metrics to systems like Prometheus, Datadog, and InfluxDB.

**Liveness Probe**:
A Kubernetes health probe that determines whether a container is alive; if failed, Kubernetes kills and restarts the pod container.

**Readiness Probe**:
A Kubernetes health probe that checks whether an application is ready to accept live traffic; if failed, the pod is removed from service endpoints without restarting.

**MDC (Mapped Diagnostic Context)**:
An SLF4J mechanism backed by `ThreadLocal` storage that allows injecting contextual key-value pairs (e.g. `traceId`, `userId`) into every log statement emitted on that thread.

**OpenAPI 3 (OAS3)**:
A vendor-neutral specification standard for describing RESTful APIs in JSON/YAML, visualized interactively through tools like Swagger UI.

## Spring Security 6, JWT & OAuth2

**SecurityFilterChain**:
An ordered pipeline of Spring Security filters that intercept incoming HTTP requests to enforce authentication, CSRF, and authorization rules.

**SecurityContextHolder**:
A framework utility providing access to the current `SecurityContext` (storing the authenticated `Authentication` principal), typically backed by `ThreadLocal` storage.

**Principal**:
The currently authenticated user, client, or identity within an application.

**GrantedAuthority**:
An individual permission (e.g. `order:write`) or role (e.g. `ROLE_ADMIN`) granted to an authenticated principal.

**DelegatingPasswordEncoder**:
A Spring Security password hashing facade that supports algorithm prefixes (e.g. `{argon2}`, `{bcrypt}`) for seamless zero-downtime hash upgrades.

**Argon2id**:
A memory-hard, GPU/ASIC-resistant cryptographic password hashing algorithm recommended by OWASP and winner of the Password Hashing Competition.

**JWT (JSON Web Token)**:
An open standard (RFC 7519) defining a compact, URL-safe method for securely transmitting claims between parties as a digitally signed JSON object.

**Method Security**:
Spring Security's mechanism for enforcing access control at the Java method level using `@PreAuthorize`, `@PostAuthorize`, and SpEL expressions.

**OAuth 2.0**:
An industry-standard delegated authorization framework enabling third-party applications to obtain limited access to an HTTP service on behalf of a user.

**OpenID Connect (OIDC 1.0)**:
An identity authentication layer built directly on top of OAuth 2.0 that provides standardized ID tokens (`id_token`) and user profile claims.

**PKCE (Proof Key for Code Exchange)**:
A cryptographic extension (RFC 7636) to the OAuth 2.0 Authorization Code flow that prevents authorization code injection and interception attacks.

## Distributed Systems & Messaging


**Idempotency**:
A property of an operation whereby performing it multiple times yields the exact same outcome as performing it once.

**Outbox Pattern**:
A distributed pattern where database changes and corresponding integration events are written atomically into a local outbox table before being published to a message broker.

**SAGA Pattern**:
A sequence of local transactions across microservices coordinated either by choreography (events) or orchestration (central coordinator) to maintain eventual consistency.

**CQRS (Command Query Responsibility Segregation)**:
An architectural pattern that separates read and update operations into distinct models to optimize performance, scaling, and security.

**Backpressure**:
A mechanism in reactive stream processing where consumers signal how much data they are able to handle, preventing producers from overwhelming downstream stages.
