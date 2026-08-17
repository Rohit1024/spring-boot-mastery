---
icon: lucide/graduation-cap
---

# Spring Boot & Enterprise Architecture Curriculum

All concepts from your comprehensive roadmap are organized into structured, progressive modules. Each lesson is focused, hands-on, and includes architectural diagrams, internal mechanics, and retrieval exercises.

---

## 🏛️ Module 1: Spring Core Fundamentals & Inversion of Control
- [x] [**0001: Spring IoC Container, Bean Scopes & Lifecycle**](0001-spring-ioc-and-bean-lifecycle.md)
- [x] [**0002: Dependency Injection Strategies (Constructor vs Setter vs Field) & @Qualifier / @Primary**](0002-dependency-injection-strategies.md)
- [x] [**0003: Spring Boot Under the Hood: Auto-Configuration, @Conditional & Starter Mechanics**](0003-spring-boot-autoconfiguration-internals.md)
- [x] [**0004: Aspect-Oriented Programming (AOP): Before, After, Around, After-Throwing Advice**](0004-aspect-oriented-programming-aop.md)
- [x] [**0005: Spring Profiles & Environment Management (`dev`, `stage`, `prod`)**](0005-spring-profiles-and-environments.md)

---

## 🌐 Module 2: RESTful Web Services & Spring MVC
- [x] [**0006: Servlet Architecture vs Spring DispatcherServlet & Web MVC Pipeline**](0006-servlet-architecture-and-dispatcherservlet.md)
- [x] [**0007: Building RESTful CRUD APIs with Controllers, RequestMapping & HTTP Status Codes**](0007-building-restful-crud-apis.md)
- [x] [**0008: Spring Bean Validation (`@Valid`, Custom Validators & Constraint Annotations)**](0008-spring-bean-validation.md)
- [x] [**0009: Global Exception Handling with `@RestControllerAdvice` & ProblemDetails**](0009-global-exception-handling.md)
- [x] [**0010: Standardizing Response Envelopes & DTO Pattern with Lombok & MapStruct**](0010-dto-pattern-and-response-envelopes.md)
- [x] [**0011: Design Patterns in Spring: Strategy & Decorator Patterns**](0011-design-patterns-strategy-decorator.md)

---

## 💾 Module 3: Persistence Mastery — Hibernate, JPA & R2DBC
- [x] [**0012: JDBC vs Hibernate ORM Internals: SessionFactory, Entity Lifecycle & Dirty Checking**](0012-jdbc-vs-hibernate-orm-internals.md)
- [x] [**0013: Spring Data JPA: Repositories, Derived Query Methods, Pagination & JPQL vs Native Queries**](0013-spring-data-jpa-repositories-and-queries.md)
- [x] [**0014: Entity Relationships (1:1, 1:N, N:N), Fetch Types & The Dreaded N+1 Problem**](0014-entity-relationships-lazy-loading-n-plus-1.md)
- [x] [**0015: Transaction Management: @Transactional, Proxy Mechanics, Propagation & Isolation Levels**](0015-transaction-management-and-propagation.md)
- [x] [**0016: Multi-DataSource Architecture & NoSQL Integration (PostgreSQL + MySQL + MongoDB)**](0016-multi-datasource-and-nosql-integration.md)
- [x] [**0017: Entity Auditing with JPA & Historical Revision Tracking with Hibernate Envers**](0017-entity-auditing-and-spring-data-envers.md)

---

## 🛠️ Module 4: Observability, Tooling & API Docs
- [x] [**0018: Supercharging Development with Spring DevTools & Live Reload**](0018-spring-boot-devtools-and-livereload.md)
- [x] [**0019: Production Health & Monitoring with Spring Boot Actuator & Metrics**](0019-production-health-actuator-and-metrics.md)
- [x] [**0020: API Documentation with OpenAPI 3 & Swagger UI**](0020-openapi-3-and-swagger-ui-documentation.md)
- [x] [**0021: Structured Application Logging with SLF4J, Logback & Mapped Diagnostic Context (MDC)**](0021-structured-logging-logback-mdc.md)
- [x] [**0022: Centralized Logging with ELK Stack (Elasticsearch, Logstash, Kibana)**](0022-centralized-logging-elk-stack.md)

---

## 🔒 Module 5: Spring Security 6, OAuth2 & Identity
- [x] [**0023: Spring Security 6 Architecture: Filter Chains, AuthenticationManager & SecurityContext**](0023-spring-security-6-architecture-filter-chains.md)
- [x] [**0024: Password Hashing (BCrypt, Argon2) & User Session Management**](0024-password-hashing-bcrypt-argon2-sessions.md)
- [x] [**0025: Stateless Authentication with JWT (JSON Web Tokens): Issuing, Validating & Filter Interception**](0025-stateless-jwt-authentication-filter.md)
- [x] [**0026: Role-Based & Permission-Based Access Control (RBAC) with Method Security (`@PreAuthorize`)**](0026-role-and-permission-based-access-control-rbac.md)
- [x] [**0027: Third-Party Authentication with Google OAuth2 & OpenID Connect (OIDC)**](0027-google-oauth2-and-openid-connect-oidc.md)

---

## 📦 Module 6: Building, Packaging & Containerizing Spring Boot Applications
- [x] [**0028: Packaging Paradigms: Fat JAR vs Layered JAR vs Multi-Stage Dockerfile**](0028-packaging-paradigms-jar-docker-layering.md)
- [x] [**0029: Daemonless Containerization with Google Jib (Maven & Gradle)**](0029-daemonless-containerization-google-jib.md)
- [x] [**0030: Multi-Cloud Artifact Registry Authentication & Portable Configuration with Jib**](0030-multi-cloud-artifact-registry-authentication-jib.md)
- [x] [**0031: GraalVM AOT Native Image Compilation**](0031-graalvm-aot-native-image-compilation.md)
- [x] [**0032: Containerizing GraalVM Native Images with Google Jib & Distroless**](0032-containerizing-graalvm-native-images-with-jib.md)

---

## 🧪 Module 7: Enterprise Testing & Quality Assurance
- [ ] **0033: Unit Testing with JUnit 5 & AssertJ**
- [ ] **0034: Mocking Dependencies with Mockito (`@Mock`, `@InjectMocks`, `verify`)**
- [ ] **0035: Integration Testing REST APIs with `@SpringBootTest` & `MockMvc`**
- [ ] **0036: Database Integration Testing with Testcontainers**

---

## ⚡ Module 8: High-Performance Caching & Messaging Systems
- [ ] **0037: Spring Cache Abstraction with Redis (`@Cacheable`, `@CachePut`, `@CacheEvict`)**
- [ ] **0038: Redis Pub/Sub Messaging for Real-Time Event Fanout**
- [ ] **0039: Apache Kafka Architecture: Topics, Partitions, Offsets & Consumer Groups**
- [ ] **0040: Kafka Producer & Consumer Integration with Spring Kafka & DLQ (Dead Letter Queue)**
- [ ] **0041: Rate Limiting Algorithms in Redis: Token Bucket, Sliding Window, Fixed Window**

---

## 🧩 Module 9: Microservices, Cloud & Distributed Patterns
- [ ] **0042: Monolith vs Microservices: System Design Principles & Service Boundaries**
- [ ] **0043: Inter-Service Communication: RestTemplate, WebClient & Spring Cloud OpenFeign**
- [ ] **0044: Service Registry & Discovery with Spring Cloud Netflix Eureka**
- [ ] **0045: API Gateway Routing & Security with Spring Cloud Gateway**
- [ ] **0046: Centralized Configuration with Spring Cloud Config Server & Dynamic Bus Refresh**
- [ ] **0047: Distributed Tracing with Micrometer Tracing / Sleuth & Zipkin**
- [ ] **0048: Fault Tolerance with Resilience4j: Circuit Breaker, Retry, Bulkhead & Rate Limiter**
- [ ] **0049: Distributed Transactions: SAGA Pattern with Kafka Choreography**
- [ ] **0050: Guaranteed Message Delivery: Transactional Outbox Pattern with PostgreSQL & Kafka**
- [ ] **0051: High-Scale Reads: CQRS Architecture**
- [ ] **0052: Distributed Idempotency: Duplicate Prevention with Redis `SETNX`**
- [ ] **0053: CAP Theorem in Action: Consistency vs Availability in Payment Systems**
- [ ] **0054: Containerization: Dockerfile Multi-Stage Builds & Docker Compose**
- [ ] **0055: Kubernetes Orchestration: Pods, Deployments, Services, ConfigMaps & Dashboard**
- [ ] **0056: Cloud CI/CD: AWS CodePipeline, Buildspec & Elastic Beanstalk Deployment**

---

## 🚀 Module 10: Reactive Programming (WebFlux) & Spring AI
- [ ] **0057: Blocking vs Non-Blocking I/O: The Reactive Paradigm at Scale**
- [ ] **0058: Project Reactor Fundamentals: Mono, Flux, Schedulers & Reactive Pipeline Model**
- [ ] **0059: Building Reactive REST APIs with Spring WebFlux**
- [ ] **0060: Non-Blocking Persistence with R2DBC & Reactive Redis (`ReactiveRedisTemplate`)**
- [ ] **0061: Real-Time Streaming with Server-Sent Events (SSE)**
- [ ] **0062: Reactive Backpressure Handling: Bounded `flatMap` & Buffer Strategies**
- [ ] **0063: Integration Testing Reactive APIs with `WebTestClient` & Testcontainers**
- [ ] **0064: Spring AI: LLM Chat Clients, Prompts & Multi-Model Integration**
- [ ] **0065: Retrieval-Augmented Generation (RAG) with Vector Stores & Embeddings in Spring AI**
- [ ] **0066: MCP (Model Context Protocol) Server & Tool Integration with Spring AI**
