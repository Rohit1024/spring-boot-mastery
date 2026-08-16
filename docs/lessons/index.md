---
icon: lucide/graduation-cap
---

# Spring Boot & Enterprise Architecture Curriculum

All concepts from your comprehensive roadmap are organized into 9 structured, progressive modules. Each lesson is focused, hands-on, and includes architectural diagrams, internal mechanics, and retrieval exercises.

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
- [ ] **0023: Spring Security 6 Architecture: Filter Chains, AuthenticationManager & SecurityContext**
- [ ] **0024: Password Hashing (BCrypt, Argon2) & User Session Management**
- [ ] **0025: Stateless Authentication with JWT (JSON Web Tokens): Issuing, Validating & Filter Interception**
- [ ] **0026: Role-Based & Permission-Based Access Control (RBAC) with Method Security (`@PreAuthorize`)**
- [ ] **0027: Third-Party Authentication with Google OAuth2 & OpenID Connect (OIDC)**

---

## 🧪 Module 6: Enterprise Testing & Quality Assurance
- [ ] **0028: Unit Testing with JUnit 5 & AssertJ**
- [ ] **0029: Mocking Dependencies with Mockito (`@Mock`, `@InjectMocks`, `verify`)**
- [ ] **0030: Integration Testing REST APIs with `@SpringBootTest` & `MockMvc`**
- [ ] **0031: Database Integration Testing with Testcontainers**

---

## ⚡ Module 7: High-Performance Caching & Messaging Systems
- [ ] **0032: Spring Cache Abstraction with Redis (`@Cacheable`, `@CachePut`, `@CacheEvict`)**
- [ ] **0033: Redis Pub/Sub Messaging for Real-Time Event Fanout**
- [ ] **0034: Apache Kafka Architecture: Topics, Partitions, Offsets & Consumer Groups**
- [ ] **0035: Kafka Producer & Consumer Integration with Spring Kafka & DLQ (Dead Letter Queue)**
- [ ] **0036: Rate Limiting Algorithms in Redis: Token Bucket, Sliding Window, Fixed Window**

---

## 🧩 Module 8: Microservices, Cloud & Distributed Patterns
- [ ] **0037: Monolith vs Microservices: System Design Principles & Service Boundaries**
- [ ] **0038: Inter-Service Communication: RestTemplate, WebClient & Spring Cloud OpenFeign**
- [ ] **0039: Service Registry & Discovery with Spring Cloud Netflix Eureka**
- [ ] **0040: API Gateway Routing & Security with Spring Cloud Gateway**
- [ ] **0041: Centralized Configuration with Spring Cloud Config Server & Dynamic Bus Refresh**
- [ ] **0042: Distributed Tracing with Micrometer Tracing / Sleuth & Zipkin**
- [ ] **0043: Fault Tolerance with Resilience4j: Circuit Breaker, Retry, Bulkhead & Rate Limiter**
- [ ] **0044: Distributed Transactions: SAGA Pattern with Kafka Choreography**
- [ ] **0045: Guaranteed Message Delivery: Transactional Outbox Pattern with PostgreSQL & Kafka**
- [ ] **0046: High-Scale Reads: CQRS Architecture**
- [ ] **0047: Distributed Idempotency: Duplicate Prevention with Redis `SETNX`**
- [ ] **0048: CAP Theorem in Action: Consistency vs Availability in Payment Systems**
- [ ] **0049: Containerization: Dockerfile Multi-Stage Builds & Docker Compose**
- [ ] **0050: Kubernetes Orchestration: Pods, Deployments, Services, ConfigMaps & Dashboard**
- [ ] **0051: Cloud CI/CD: AWS CodePipeline, Buildspec & Elastic Beanstalk Deployment**

---

## 🚀 Module 9: Reactive Programming (WebFlux) & Spring AI
- [ ] **0052: Blocking vs Non-Blocking I/O: The Reactive Paradigm at Scale**
- [ ] **0053: Project Reactor Fundamentals: Mono, Flux, Schedulers & Reactive Pipeline Model**
- [ ] **0054: Building Reactive REST APIs with Spring WebFlux**
- [ ] **0055: Non-Blocking Persistence with R2DBC & Reactive Redis (`ReactiveRedisTemplate`)**
- [ ] **0056: Real-Time Streaming with Server-Sent Events (SSE)**
- [ ] **0057: Reactive Backpressure Handling: Bounded `flatMap` & Buffer Strategies**
- [ ] **0058: Integration Testing Reactive APIs with `WebTestClient` & Testcontainers**
- [ ] **0059: Spring AI: LLM Chat Clients, Prompts & Multi-Model Integration**
- [ ] **0060: Retrieval-Augmented Generation (RAG) with Vector Stores & Embeddings in Spring AI**
- [ ] **0061: MCP (Model Context Protocol) Server & Tool Integration with Spring AI**
