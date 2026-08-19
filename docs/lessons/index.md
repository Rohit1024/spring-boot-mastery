---
icon: lucide/graduation-cap
---

# Spring Boot and enterprise architecture curriculum

Structured modules covering core container mechanics, data persistence, security, cloud architecture, and reactive systems. Each lesson includes diagrams, code examples, and practice questions.

---

## Module 1: Spring Core fundamentals and inversion of control
- [x] [**0001: Spring IoC container, bean scopes, and lifecycle**](0001-spring-ioc-and-bean-lifecycle.md)
- [x] [**0002: Dependency injection strategies and resolving ambiguities**](0002-dependency-injection-strategies.md)
- [x] [**0003: Spring Boot auto-configuration, @Conditional, and starters**](0003-spring-boot-autoconfiguration-internals.md)
- [x] [**0004: Aspect-Oriented Programming (AOP) and advice types**](0004-aspect-oriented-programming-aop.md)
- [x] [**0005: Spring profiles and multi-environment configuration**](0005-spring-profiles-and-environments.md)

---

## Module 2: RESTful web services and Spring MVC
- [x] [**0006: Servlet architecture vs Spring DispatcherServlet and Web MVC pipeline**](0006-servlet-architecture-and-dispatcherservlet.md)
- [x] [**0007: Building RESTful CRUD APIs with controllers, RequestMapping, and HTTP status codes**](0007-building-restful-crud-apis.md)
- [x] [**0008: Spring bean validation (@Valid, custom validators, and constraint annotations)**](0008-spring-bean-validation.md)
- [x] [**0009: Global exception handling with @RestControllerAdvice and ProblemDetails**](0009-global-exception-handling.md)
- [x] [**0010: Standardizing response envelopes and DTO pattern with Lombok and MapStruct**](0010-dto-pattern-and-response-envelopes.md)
- [x] [**0011: Design patterns in Spring: Strategy and Decorator patterns**](0011-design-patterns-strategy-decorator.md)

---

## Module 3: Persistence: Hibernate, JPA, and R2DBC
- [x] [**0012: JDBC vs Hibernate ORM internals: SessionFactory, entity lifecycle, and dirty checking**](0012-jdbc-vs-hibernate-orm-internals.md)
- [x] [**0013: Spring Data JPA: Repositories, derived query methods, pagination, and JPQL vs native queries**](0013-spring-data-jpa-repositories-and-queries.md)
- [x] [**0014: Entity relationships (1:1, 1:N, N:N), fetch types, and N+1 query troubleshooting**](0014-entity-relationships-lazy-loading-n-plus-1.md)
- [x] [**0015: Transaction management: @Transactional, proxy mechanics, propagation, and isolation levels**](0015-transaction-management-and-propagation.md)
- [x] [**0016: Multi-DataSource architecture and NoSQL integration (PostgreSQL, MySQL, MongoDB)**](0016-multi-datasource-and-nosql-integration.md)
- [x] [**0017: Entity auditing with JPA and revision tracking with Hibernate Envers**](0017-entity-auditing-and-spring-data-envers.md)

---

## Module 4: Observability, tooling, and API docs
- [x] [**0018: Development workflow with Spring DevTools and LiveReload**](0018-spring-boot-devtools-and-livereload.md)
- [x] [**0019: Production health and monitoring with Spring Boot Actuator and metrics**](0019-production-health-actuator-and-metrics.md)
- [x] [**0020: API documentation with OpenAPI 3 and Swagger UI**](0020-openapi-3-and-swagger-ui-documentation.md)
- [x] [**0021: Structured application logging with SLF4J, Logback, and MDC**](0021-structured-logging-logback-mdc.md)
- [x] [**0022: Centralized logging with the ELK stack**](0022-centralized-logging-elk-stack.md)

---

## Module 5: Spring Security 6, OAuth2, and identity
- [x] [**0023: Spring Security 6 architecture: Filter chains, AuthenticationManager, and SecurityContext**](0023-spring-security-6-architecture-filter-chains.md)
- [x] [**0024: Password hashing (BCrypt, Argon2) and user session management**](0024-password-hashing-bcrypt-argon2-sessions.md)
- [x] [**0025: Stateless authentication with JWT: Issuing, validating, and filter interception**](0025-stateless-jwt-authentication-filter.md)
- [x] [**0026: Role-based and permission-based access control (RBAC) with method security**](0026-role-and-permission-based-access-control-rbac.md)
- [x] [**0027: Third-party authentication with Google OAuth2 and OpenID Connect (OIDC)**](0027-google-oauth2-and-openid-connect-oidc.md)

---

## Module 6: Packaging and containerizing Spring Boot applications
- [x] [**0028: Packaging paradigms: Fat JAR vs layered JAR vs multi-stage Dockerfile**](0028-packaging-paradigms-jar-docker-layering.md)
- [x] [**0029: Daemonless containerization with Google Jib (Maven and Gradle)**](0029-daemonless-containerization-google-jib.md)
- [x] [**0030: Multi-cloud artifact registry authentication and configuration with Jib**](0030-multi-cloud-artifact-registry-authentication-jib.md)
- [x] [**0031: GraalVM AOT native image compilation**](0031-graalvm-aot-native-image-compilation.md)
- [x] [**0032: Containerizing GraalVM native images with Google Jib and Distroless**](0032-containerizing-graalvm-native-images-with-jib.md)

---

## Module 7: Batch processing, task scheduling, and distributed locking
- [x] [**0033: Spring Batch architecture and JobRepository persistence**](0033-spring-batch-architecture-jobrepository.md)
- [x] [**0034: Chunk-oriented processing: Readers, processors, and writers**](0034-chunk-oriented-processing-readers-writers.md)
- [x] [**0035: Fault tolerance in Spring Batch: Skip, retry, and rollback policies**](0035-fault-tolerance-skip-retry-policies.md)
- [x] [**0036: High-scale batch processing: Multithreaded steps and partitioning**](0036-multithreaded-steps-and-partitioning.md)
- [x] [**0037: Task scheduling with Quartz and distributed locking with ShedLock**](0037-quartz-scheduler-and-shedlock-distributed-locking.md)

---

## Module 8: Alternative API protocols: GraphQL, gRPC, and WebSockets
- [x] [**0038: Spring for GraphQL: Schema design, queries, mutations, and GraphiQL**](0038-spring-graphql-schema-queries-mutations.md)
- [x] [**0039: GraphQL batch mapping, DataLoaders, and subscriptions**](0039-graphql-batch-mapping-dataloaders-subscriptions.md)
- [x] [**0040: Microservice RPC with Spring gRPC and Protocol Buffers**](0040-spring-grpc-and-protocol-buffers-microservices.md)
- [x] [**0041: Real-time messaging with WebSockets and STOMP**](0041-websockets-and-stomp-bidirectional-messaging.md)

---

## Module 9: Architecture paradigms and modern Java features
- [x] [**0042: Modular monoliths with Spring Modulith: DDD and boundary enforcement**](0042-spring-modulith-modular-monoliths-ddd.md)
- [x] [**0043: Decoupling modules with transactional event publication**](0043-transactional-event-publication-spring-modulith.md)
- [x] [**0044: Concurrency: Java 21 virtual threads (Project Loom) in Spring Boot**](0044-java-virtual-threads-project-loom-spring-boot.md)

---

## Module 10: Vendor-neutral observability: Prometheus, Grafana, and OpenTelemetry
- [x] [**0045: Production metrics with Prometheus: Scraping, PromQL, and alert rules**](0045-production-metrics-prometheus-scraping-promql.md)
- [x] [**0046: Dashboarding with Grafana: The RED and USE metric methods**](0046-grafana-dashboards-red-and-use-metrics.md)
- [x] [**0047: OpenTelemetry: Vendor-neutral tracing, spans, and OTLP collectors**](0047-opentelemetry-otel-tracing-and-otlp-collectors.md)

---

## Module 11: Enterprise testing and quality assurance
- [x] [**0048: Unit testing with JUnit 5 and AssertJ**](0048-unit-testing-junit-5-assertj.md)
- [x] [**0049: Mocking dependencies with Mockito (@Mock, @InjectMocks, verify)**](0049-mocking-dependencies-with-mockito.md)
- [x] [**0050: Integration testing REST APIs with @SpringBootTest and MockMvc**](0050-integration-testing-rest-apis-mockmvc.md)
- [x] [**0051: Database integration testing with Testcontainers**](0051-database-integration-testing-testcontainers.md)

---

## Module 12: High-performance caching and messaging systems
- [x] [**0052: Spring Cache abstraction with Redis (@Cacheable, @CachePut, @CacheEvict)**](0052-spring-cache-abstraction-redis.md)
- [x] [**0053: Redis Pub/Sub messaging for real-time event fanout**](0053-redis-pub-sub-messaging.md)
- [x] [**0054: Apache Kafka architecture: Topics, partitions, offsets, and consumer groups**](0054-apache-kafka-architecture-and-internals.md)
- [x] [**0055: Kafka producer and consumer integration with Spring Kafka and DLQ**](0055-kafka-producer-consumer-spring-dlq.md)
- [x] [**0056: Rate limiting algorithms in Redis: Token bucket, sliding window, fixed window**](0056-redis-rate-limiting-algorithms.md)

---

## Module 13: Microservices, cloud, and distributed patterns
- [x] [**0057: Monolith vs microservices: System design principles and service boundaries**](0057-monolith-vs-microservices-system-design.md)
- [x] [**0058: Inter-service communication: RestTemplate, WebClient, and Spring Cloud OpenFeign**](0058-interservice-communication-feign-webclient.md)
- [x] [**0059: Service registry and discovery with Spring Cloud Netflix Eureka**](0059-service-registry-discovery-eureka.md)
- [x] [**0060: API Gateway routing and security with Spring Cloud Gateway**](0060-api-gateway-routing-security-spring-cloud.md)
- [x] [**0061: Centralized configuration with Spring Cloud Config Server and dynamic bus refresh**](0061-centralized-config-server-bus-refresh.md)
- [x] [**0062: Distributed tracing with Micrometer Tracing and Zipkin**](0062-distributed-tracing-micrometer-zipkin.md)
- [x] [**0063: Fault tolerance with Resilience4j: Circuit Breaker, Retry, Bulkhead, and Rate Limiter**](0063-fault-tolerance-resilience4j.md)
- [x] [**0064: Distributed transactions: Saga pattern with Kafka choreography**](0064-distributed-transactions-saga-pattern.md)
- [x] [**0065: Guaranteed message delivery: Transactional Outbox pattern with PostgreSQL and Kafka**](0065-transactional-outbox-pattern-postgres-kafka.md)
- [x] [**0066: High-scale reads: CQRS architecture**](0066-high-scale-reads-cqrs-architecture.md)
- [x] [**0067: Distributed idempotency: Duplicate prevention with Redis SETNX**](0067-distributed-idempotency-redis-setnx.md)
- [x] [**0068: CAP theorem in action: Consistency vs availability in payment systems**](0068-cap-theorem-consistency-availability-payments.md)
- [x] [**0069: Containerization: Dockerfile multi-stage builds and Docker Compose**](0069-dockerfile-multistage-builds-docker-compose.md)
- [x] [**0070: Kubernetes orchestration: Pods, deployments, services, and ConfigMaps**](0070-kubernetes-orchestration-pods-services.md)
- [x] [**0071: Cloud CI/CD: AWS CodePipeline, Buildspec, and Elastic Beanstalk deployment**](0071-cloud-cicd-aws-codepipeline-beanstalk.md)

---

## Module 14: Reactive programming (WebFlux) and Spring AI
- [x] [**0072: Blocking vs non-blocking I/O: The reactive model at scale**](0072-blocking-vs-nonblocking-reactive-paradigm.md)
- [x] [**0073: Project Reactor fundamentals: Mono, Flux, Schedulers, and reactive streams**](0073-project-reactor-mono-flux-schedulers.md)
- [x] [**0074: Building reactive REST APIs with Spring WebFlux**](0074-building-reactive-rest-apis-spring-webflux.md)
- [x] [**0075: Non-blocking persistence with R2DBC and Reactive Redis**](0075-nonblocking-persistence-r2dbc-reactive-redis.md)
- [x] [**0076: Real-time streaming with Server-Sent Events (SSE)**](0076-realtime-streaming-server-sent-events-sse.md)
- [x] [**0077: Reactive backpressure handling: Bounded flatMap and buffer strategies**](0077-reactive-backpressure-flatmap-buffer-strategies.md)
- [x] [**0078: Integration testing reactive APIs with WebTestClient and Testcontainers**](0078-integration-testing-reactive-webtestclient-testcontainers.md)
- [x] [**0079: Spring AI: LLM Chat Clients, prompts, and multi-model integration**](0079-spring-ai-llm-chatclient-prompts.md)
- [x] [**0080: Retrieval-Augmented Generation (RAG) with vector stores and embeddings in Spring AI**](0080-rag-vector-stores-embeddings-spring-ai.md)
- [x] [**0081: MCP (Model Context Protocol) server and tool integration with Spring AI**](0081-mcp-server-tool-integration-spring-ai.md)
