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

## ⚙️ Module 7: Batch Processing, Enterprise Schedulers & Distributed Locking
- [x] [**0033: Spring Batch Core Architecture & JobRepository Persistence**](0033-spring-batch-architecture-jobrepository.md)
- [x] [**0034: Chunk-Oriented Processing: Readers, Processors & Writers**](0034-chunk-oriented-processing-readers-writers.md)
- [x] [**0035: Fault Tolerance in Spring Batch: Skip, Retry & Rollback Policies**](0035-fault-tolerance-skip-retry-policies.md)
- [x] [**0036: High-Scale Batch Processing: Multi-Threaded Steps & Partitioning**](0036-multithreaded-steps-and-partitioning.md)
- [x] [**0037: Enterprise Task Scheduling with Quartz & Distributed Locking with ShedLock**](0037-quartz-scheduler-and-shedlock-distributed-locking.md)

---

## 🛰️ Module 8: Alternative API Protocols — GraphQL, gRPC & WebSockets
- [x] [**0038: Spring for GraphQL: Schema Design, Queries, Mutations & GraphiQL**](0038-spring-graphql-schema-queries-mutations.md)
- [x] [**0039: GraphQL Batch Mapping, DataLoaders & Real-Time Subscriptions**](0039-graphql-batch-mapping-dataloaders-subscriptions.md)
- [x] [**0040: High-Performance Microservice RPC with Spring gRPC & Protocol Buffers**](0040-spring-grpc-and-protocol-buffers-microservices.md)
- [x] [**0041: Full-Duplex Real-Time Messaging with WebSockets & STOMP**](0041-websockets-and-stomp-bidirectional-messaging.md)

---

## 🏗️ Module 9: Architecture Paradigms & Modern Java Features
- [x] [**0042: Modular Monoliths with Spring Modulith: DDD & Boundary Enforcement**](0042-spring-modulith-modular-monoliths-ddd.md)
- [x] [**0043: Decoupling Modules with Transactional Event Publication**](0043-transactional-event-publication-spring-modulith.md)
- [x] [**0044: Lightweight Concurrency: Java 21 Virtual Threads (Project Loom) in Spring Boot**](0044-java-virtual-threads-project-loom-spring-boot.md)

---

## 📈 Module 10: Vendor-Neutral Observability — Prometheus, Grafana & OpenTelemetry
- [x] [**0045: Production Metrics with Prometheus: Scraping, PromQL & Alert Rules**](0045-production-metrics-prometheus-scraping-promql.md)
- [x] [**0046: Enterprise Dashboarding with Grafana: The RED & USE Metrics Methods**](0046-grafana-dashboards-red-and-use-metrics.md)
- [x] [**0047: OpenTelemetry (OTel): Vendor-Neutral Tracing, Spans & OTLP Collectors**](0047-opentelemetry-otel-tracing-and-otlp-collectors.md)

---

## 🧪 Module 11: Enterprise Testing & Quality Assurance
- [x] [**0048: Unit Testing with JUnit 5 & AssertJ**](0048-unit-testing-junit-5-assertj.md)
- [x] [**0049: Mocking Dependencies with Mockito (`@Mock`, `@InjectMocks`, `verify`)**](0049-mocking-dependencies-with-mockito.md)
- [x] [**0050: Integration Testing REST APIs with `@SpringBootTest` & `MockMvc`**](0050-integration-testing-rest-apis-mockmvc.md)
- [x] [**0051: Database Integration Testing with Testcontainers**](0051-database-integration-testing-testcontainers.md)

---

## ⚡ Module 12: High-Performance Caching & Messaging Systems
- [x] [**0052: Spring Cache Abstraction with Redis (`@Cacheable`, `@CachePut`, `@CacheEvict`)**](0052-spring-cache-abstraction-redis.md)
- [x] [**0053: Redis Pub/Sub Messaging for Real-Time Event Fanout**](0053-redis-pub-sub-messaging.md)
- [x] [**0054: Apache Kafka Architecture: Topics, Partitions, Offsets & Consumer Groups**](0054-apache-kafka-architecture-and-internals.md)
- [x] [**0055: Kafka Producer & Consumer Integration with Spring Kafka & DLQ (Dead Letter Queue)**](0055-kafka-producer-consumer-spring-dlq.md)
- [x] [**0056: Rate Limiting Algorithms in Redis: Token Bucket, Sliding Window, Fixed Window**](0056-redis-rate-limiting-algorithms.md)

---

## 🧩 Module 13: Microservices, Cloud & Distributed Patterns
- [x] [**0057: Monolith vs Microservices: System Design Principles & Service Boundaries**](0057-monolith-vs-microservices-system-design.md)
- [x] [**0058: Inter-Service Communication: RestTemplate, WebClient & Spring Cloud OpenFeign**](0058-interservice-communication-feign-webclient.md)
- [x] [**0059: Service Registry & Discovery with Spring Cloud Netflix Eureka**](0059-service-registry-discovery-eureka.md)
- [x] [**0060: API Gateway Routing & Security with Spring Cloud Gateway**](0060-api-gateway-routing-security-spring-cloud.md)
- [x] [**0061: Centralized Configuration with Spring Cloud Config Server & Dynamic Bus Refresh**](0061-centralized-config-server-bus-refresh.md)
- [x] [**0062: Distributed Tracing with Micrometer Tracing / Sleuth & Zipkin**](0062-distributed-tracing-micrometer-zipkin.md)
- [x] [**0063: Fault Tolerance with Resilience4j: Circuit Breaker, Retry, Bulkhead & Rate Limiter**](0063-fault-tolerance-resilience4j.md)
- [x] [**0064: Distributed Transactions: SAGA Pattern with Kafka Choreography**](0064-distributed-transactions-saga-pattern.md)
- [x] [**0065: Guaranteed Message Delivery: Transactional Outbox Pattern with PostgreSQL & Kafka**](0065-transactional-outbox-pattern-postgres-kafka.md)
- [x] [**0066: High-Scale Reads: CQRS Architecture**](0066-high-scale-reads-cqrs-architecture.md)
- [x] [**0067: Distributed Idempotency: Duplicate Prevention with Redis `SETNX`**](0067-distributed-idempotency-redis-setnx.md)
- [x] [**0068: CAP Theorem in Action: Consistency vs Availability in Payment Systems**](0068-cap-theorem-consistency-availability-payments.md)
- [x] [**0069: Containerization: Dockerfile Multi-Stage Builds & Docker Compose**](0069-dockerfile-multistage-builds-docker-compose.md)
- [x] [**0070: Kubernetes Orchestration: Pods, Deployments, Services, ConfigMaps & Dashboard**](0070-kubernetes-orchestration-pods-services.md)
- [x] [**0071: Cloud CI/CD: AWS CodePipeline, Buildspec & Elastic Beanstalk Deployment**](0071-cloud-cicd-aws-codepipeline-beanstalk.md)

---

## 🚀 Module 14: Reactive Programming (WebFlux) & Spring AI
- [x] [**0072: Blocking vs Non-Blocking I/O: The Reactive Paradigm at Scale**](0072-blocking-vs-nonblocking-reactive-paradigm.md)
- [x] [**0073: Project Reactor Fundamentals: Mono, Flux, Schedulers & Reactive Pipeline Model**](0073-project-reactor-mono-flux-schedulers.md)
- [x] [**0074: Building Reactive REST APIs with Spring WebFlux**](0074-building-reactive-rest-apis-spring-webflux.md)
- [x] [**0075: Non-Blocking Persistence with R2DBC & Reactive Redis (`ReactiveRedisTemplate`)**](0075-nonblocking-persistence-r2dbc-reactive-redis.md)
- [x] [**0076: Real-Time Streaming with Server-Sent Events (SSE)**](0076-realtime-streaming-server-sent-events-sse.md)
- [x] [**0077: Reactive Backpressure Handling: Bounded `flatMap` & Buffer Strategies**](0077-reactive-backpressure-flatmap-buffer-strategies.md)
- [x] [**0078: Integration Testing Reactive APIs with `WebTestClient` & Testcontainers**](0078-integration-testing-reactive-webtestclient-testcontainers.md)
- [x] [**0079: Spring AI: LLM Chat Clients, Prompts & Multi-Model Integration**](0079-spring-ai-llm-chatclient-prompts.md)
- [x] [**0080: Retrieval-Augmented Generation (RAG) with Vector Stores & Embeddings in Spring AI**](0080-rag-vector-stores-embeddings-spring-ai.md)
- [x] [**0081: MCP (Model Context Protocol) Server & Tool Integration with Spring AI**](0081-mcp-server-tool-integration-spring-ai.md)
