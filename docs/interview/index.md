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

## ⚙️ Batch Processing, Schedulers & Distributed Locking
- **Spring Batch Domain Model**: Walk through the hierarchy of `Job`, `JobInstance`, `JobExecution`, `Step`, `StepExecution`, and `ExecutionContext`. How do identifying vs non-identifying `JobParameters` control restartability?
- **Chunk-Oriented Processing**: Explain the contract of `ItemReader`, `ItemProcessor`, and `ItemWriter`. What does returning `null` from each component signify to the framework?
- **Transaction Commit Boundaries**: How does the `chunk(size, transactionManager)` configuration define transaction rollback and commit boundaries during batch runs?
- **Skip vs Retry Policies**: When would you configure `.skip(Class)` versus `.retry(Class)`? How does `skipLimit` protect against runaway corrupt data processing?
- **Dead-Letter Auditing with `SkipListener`**: How do you capture and persist skipped records during `onSkipInRead`, `onSkipInProcess`, and `onSkipInWrite` for audit compliance?
- **Multi-Threaded Step Thread-Safety**: Why is `FlatFileItemReader` unsafe in multi-threaded steps by default, and how do `SynchronizedItemStreamReader` and `saveState(false)` resolve concurrency collisions?
- **Step Partitioning vs Multi-Threaded Steps**: Contrast local Master-Worker Step Partitioning with Multi-Threaded Steps in terms of thread isolation, database partitioning, and checkpoint restartability.
- **Multi-Instance `@Scheduled` Collision**: Why does standard Spring `@Scheduled` cause catastrophic race conditions when running in a multi-pod Kubernetes deployment?
- **ShedLock Distributed Locking**: How does ShedLock coordinate distributed task execution via relational tables (`shedlock`) or Redis? Explain the importance of `lockAtMostFor` and `lockAtLeastFor`.
- **Clustered Quartz Failover**: How does Quartz Scheduler leverage shared database tables (`QRTZ_*`) to provide cluster failover and misfire handling across surviving server nodes?

---

## 🛰️ Alternative API Protocols (GraphQL, gRPC & WebSockets)
- **Over-fetching vs Under-fetching**: Contrast REST API endpoint fixed response structures with GraphQL client-specified document queries.
- **GraphQL Schema-First Design**: How does Spring for GraphQL map controller methods annotated with `@QueryMapping` and `@MutationMapping` to fields in `schema.graphqls`?
- **GraphQL N+1 Problem & `@BatchMapping`**: Explain why nested field resolvers create an N+1 database query waterfall. How does `@BatchMapping` batch parent entity keys into a single `WHERE id IN (...)` SQL query?
- **GraphQL Subscriptions over WebSocket**: How do `@SubscriptionMapping` controller methods stream real-time push events using Project Reactor `Flux<T>` over a persistent WebSocket connection?
- **gRPC Protobuf vs REST JSON**: Why is Protocol Buffers binary serialization 5-10x faster and significantly smaller in bandwidth footprint than text-based JSON?
- **HTTP/2 Multiplexing in gRPC**: How does gRPC execute multiple parallel bidirectional RPC calls across a single long-lived TCP connection without head-of-line blocking?
- **gRPC Service & Client Implementation**: Walk through creating a `.proto` service definition, implementing the generated base class with `@GrpcService`, and injecting a stub with `@GrpcClient`.
- **Unary vs Streaming RPC**: Contrast Unary, Server-Streaming, Client-Streaming, and Bidirectional Streaming RPC patterns with practical microservice use cases.
- **STOMP over WebSockets**: Why is STOMP required on top of raw WebSockets to provide message routing destinations (`/topic`, `/queue`, `/app`) and frame-based pub/sub semantics?
- **Scaling WebSockets Across Kubernetes Pods**: Why does Spring's in-memory simple message broker fail in multi-pod deployments, and how does an external STOMP Broker Relay (RabbitMQ) synchronize messages across nodes?

---

## 🏗️ Architecture Paradigms & Modern Java Features (Spring Modulith & Virtual Threads)
- **Modular Monolith vs Microservices**: Why is a Modular Monolith with Spring Modulith preferred over microservices for domain systems with high transactional cohesion?
- **Module Encapsulation Rules**: How does Spring Modulith enforce package encapsulation (public root package vs hidden `*.internal` sub-packages)?
- **Architectural Verification with ArchUnit**: How does `ApplicationModules.of(App.class).verify()` detect illegal inter-module package imports and circular dependencies at test time?
- **Transactional Event Publication (Outbox)**: Explain how Spring Modulith's `event_publication` table prevents event loss during JVM crashes following a database commit.
- **`@ApplicationModuleListener` Mechanics**: What three annotations (`@Async`, `@Transactional(REQUIRES_NEW)`, `@TransactionalEventListener(AFTER_COMMIT)`) are combined under `@ApplicationModuleListener`?
- **Incomplete Event Recovery**: How do you detect and resubmit uncompleted event publications using `IncompleteEventPublications`?
- **Platform Threads vs Virtual Threads**: Contrast the 1:1 OS kernel thread model (~1MB stack, 200 Tomcat limit) with Java 21's M:N Loom continuations (~1KB stack, millions of threads).
- **Virtual Thread Unmounting Lifecycle**: What happens when a Virtual Thread executes a blocking JDBC query or `RestTemplate` call? How does `ForkJoinPool` schedule carrier threads?
- **Carrier Thread Pinning**: Why does executing a blocking I/O call inside a `synchronized` block pin the OS carrier thread, and how does refactoring to `ReentrantLock` resolve this?
- **Virtual Thread Anti-Patterns**: Why is pooling Virtual Threads (e.g. `newFixedThreadPool`) an anti-pattern? How should concurrency limits be enforced instead (e.g. `Semaphore`)?

---

## 📈 Vendor-Neutral Observability (Prometheus, Grafana & OpenTelemetry)
- **Pull vs Push Metrics Collection**: Why does Prometheus use a pull-based scraping model over `/actuator/prometheus`, and what are its advantages for cloud-native microservices?
- **Histogram Buckets vs Summaries**: Why must `percentiles-histogram.http.server.requests: true` be enabled in Spring Boot to compute P95/P99 latency with PromQL's `histogram_quantile()`?
- **PromQL `rate()` vs `increase()`**: Why is `rate()` required when computing per-second request throughput on monotonically increasing Prometheus counters?
- **Prometheus Alerting Architecture**: Explain the pipeline from Prometheus rule evaluation (`expr`) to Alertmanager grouping, deduplication, and PagerDuty notification routing.
- **The RED Method**: How do you structure a production service dashboard around Rate (throughput), Errors (5xx rate), and Duration (latency quantiles)?
- **The USE Method**: How do you diagnose internal system bottlenecks (JVM memory, HikariCP connection pool, and thread queues) using Utilization, Saturation, and Errors?
- **OpenTelemetry Core Architecture**: What is the relationship between Traces, Spans, Span Context, and Baggage in distributed tracing?
- **W3C TraceContext Specification**: Explain the anatomy of the `traceparent` HTTP header (`version`, `trace-id`, `parent-span-id`, `trace-flags`) used to propagate context across microservices.
- **OpenTelemetry Collector Pipeline**: How do Receivers, Processors (batching, memory limiter), and Exporters in the OTel Collector decouple Spring Boot services from APM backends?
- **Observability Correlation**: How does injecting `traceId` and `spanId` into SLF4J MDC enable 1-click navigation from Grafana Loki log lines to distributed trace waterfalls in Tempo/Jaeger?

---

## 🧪 Enterprise Testing & Quality Assurance (JUnit 5, Mockito & Testcontainers)
- **JUnit 5 Lifecycle**: Explain the execution sequence and lifecycle boundaries of `@BeforeAll`, `@BeforeEach`, `@Test`, `@AfterEach`, and `@AfterAll`.
- **Parameterized Testing**: How do `@ValueSource`, `@CsvSource`, and `@MethodSource` reduce test code duplication in JUnit 5?
- **AssertJ Fluent Assertions**: Why is AssertJ preferred over standard JUnit assertions for collection inspections (`.extracting()`, `.containsExactly()`) and deep object graph comparisons (`.usingRecursiveComparison()`)?
- **`@Mock` vs `@Spy` in Mockito**: Contrast a dynamic mock proxy with a real spy instance, and explain how un-stubbed method calls are handled in each.
- **`@InjectMocks` Mechanics**: How does Mockito instantiate the target class and resolve constructor, setter, or field injection of mocks?
- **Argument Capturing**: When should `ArgumentCaptor<T>` be utilized instead of exact parameter matching inside `verify()`?
- **`@WebMvcTest` vs `@SpringBootTest`**: Why is sliced web testing with `@WebMvcTest` preferred for REST controller testing over full `@SpringBootTest`?
- **MockMvc Request Lifecycle**: How does `MockMvc` simulate the `DispatcherServlet`, filter chains, argument resolvers, and exception handlers without binding to an OS TCP port?
- **H2 In-Memory Testing Trap**: Why does relying on H2 for testing production PostgreSQL or MySQL applications create high-risk production bugs?
- **Testcontainers & `@ServiceConnection`**: How does Spring Boot 3.1+ `@ServiceConnection` dynamically inject Docker container network coordinates into Spring Boot's DataSource configuration?

---

## ⚡ High-Performance Caching & Messaging Systems (Redis & Apache Kafka)
- **Spring Cache Abstraction**: Contrast `@Cacheable`, `@CachePut`, and `@CacheEvict`. How does the Spring caching AOP interceptor evaluate SpEL expressions and coordinate with `RedisCacheManager`?
- **Cache Stampede (Thundering Herd)**: What happens when a hot cache key expires under 10,000 req/sec traffic? How does `@Cacheable(sync = true)` or a distributed Redis mutex lock resolve this?
- **Redis Serialization**: Why is `JdkSerializationRedisSerializer` dangerous in production, and how does configuring `GenericJackson2JsonRedisSerializer` or typed JSON serializers protect microservices?
- **Redis Pub/Sub vs Kafka vs Redis Streams**: When should you select ephemeral Redis Pub/Sub (e.g. L1 cache invalidation / WebSocket fanout) versus persistent, replayable Apache Kafka commit logs?
- **Kafka Storage Architecture**: Explain why Kafka is exceptionally fast despite writing to disk. How do sequential I/O, segment files (`.log`, `.index`), OS PageCache, and Linux `sendfile` zero-copy I/O cooperate?
- **Partitions & Scalability**: Why is ordering guaranteed only within a partition and not across a topic? What happens to throughput and idle resources when consumer group members outnumber topic partitions?
- **Producer Reliability (`acks=all` & Idempotence)**: How do `acks=all`, `enable.idempotence=true`, and `max.in.flight.requests.per.connection=5` guarantee exactly-once delivery from producer to broker?
- **Kafka Consumer Rebalance Storms**: What causes `CommitFailedException` in high-throughput consumers, and how do you tune `max.poll.records`, `max.poll.interval.ms`, and `CooperativeStickyAssignor`?
- **Poison Pill Handling**: How does `ErrorHandlingDeserializer` prevent malformed JSON payloads from deadlocking the Kafka polling loop?
- **Non-Blocking Retries with `@RetryableTopic`**: How does Spring Kafka route failed records to separate retry topics with exponential backoff and ultimately a Dead Letter Topic (DLT) without blocking subsequent partition records?
- **Rate Limiting Algorithms in Redis**: Compare Fixed Window Counter, Sliding Window Log, Sliding Window Counter, and Token Bucket. Why are Redis Lua scripts required for atomic distributed rate limiting?

---

## 🧩 Microservices, Cloud & Distributed Patterns
- **Database-per-Service Anti-Pattern**: Why is sharing a database schema across multiple microservices considered an architectural anti-pattern?
- **Inter-Service Communication**: Contrast `RestClient`, `WebClient`, and `Spring Cloud OpenFeign`. When should a team adopt declarative Feign interfaces over programmatic WebClient calls?
- **Service Discovery & Self-Preservation**: How does Eureka detect network partitions, and why does Self-Preservation mode prevent healthy instances from being prematurely purged?
- **API Gateway Architecture**: Why is Spring Cloud Gateway built on Spring WebFlux and Netty rather than Spring MVC and Tomcat? Explain how Route Predicates, Gateway Filters, and Global Filters interact.
- **Centralized Configuration & Bus Refresh**: How does Spring Cloud Config Server integrate with Spring Cloud Bus and Kafka to dynamically reload `@RefreshScope` beans across 50 running instances without restarting JVMs?
- **Distributed Tracing & W3C Context**: Explain how `traceId` and `spanId` are propagated across HTTP headers (`traceparent`) and Kafka record headers using Micrometer Tracing.
- **Resilience4j Circuit Breaker**: Detail the state transitions (`CLOSED` -> `OPEN` -> `HALF_OPEN`). How do slow call rate thresholds, sliding windows, and Bulkheads prevent cascading thread starvation?
- **SAGA vs 2PC**: Why is Two-Phase Commit an anti-pattern in microservices, and how does SAGA choreography handle rollbacks via compensating transactions?
- **Transactional Outbox**: How do you guarantee zero-loss message publishing between PostgreSQL and Apache Kafka? Contrast scheduled polling with `SKIP LOCKED` versus Debezium CDC.
- **CQRS Architecture**: How do you maintain eventual consistency between the command (write) database and query (read) search indices? What UI strategies mitigate read lag?
- **Distributed Idempotency**: How does atomic Redis `SETNX` with a TTL prevent duplicate charges on network retries and double-submit user clicks?
- **CAP vs PACELC**: Explain the PACELC theorem using PostgreSQL (PC/EC) and DynamoDB (PA/EL) as examples. How does JPA `@Version` optimistic locking defend CP financial ledgers?
- **Container Optimization**: How do Spring Boot Layered JARs and multi-stage Dockerfiles reduce deployment build times and image vulnerability attack surfaces?
- **Kubernetes Probes**: Why must Kubernetes Readiness Probes point to isolated Actuator readiness sub-groups rather than general database health endpoints?
- **Cloud Deployment Strategies**: Compare All-at-Once, Rolling, Rolling with Additional Batch, and Blue/Green deployment strategies in terms of downtime, cost, and rollback safety.

---

## 🚀 Reactive Programming (WebFlux) & Spring AI
- **WebFlux vs MVC + Virtual Threads**: How does the Netty Event Loop model compare to Java 21 Virtual Threads on Tomcat? When should an architect choose WebFlux over Virtual Threads?
- **Reactive Streams Specification**: Detail the roles of `Publisher`, `Subscriber`, and `Subscription`. How does `Subscription.request(long n)` enforce demand-driven backpressure?
- **`map` vs `flatMap` vs `concatMap`**: What are the performance, concurrency, and ordering differences when transforming streams with Project Reactor?
- **`publishOn` vs `subscribeOn`**: Explain where thread execution context switches in a Project Reactor pipeline when applying these two operators.
- **R2DBC Mechanics**: Why can't JPA/Hibernate run inside a high-throughput WebFlux service? How does `TransactionalOperator` coordinate non-blocking transactions?
- **Server-Sent Events (SSE)**: Compare SSE with WebSockets in terms of transport protocol, firewalls, HTTP/2 multiplexing, and automatic browser reconnection (`Last-Event-ID`).
- **Reactive Backpressure Overflow Strategies**: How do `onBackpressureBuffer`, `onBackpressureDrop`, and `onBackpressureLatest` prevent JVM heap exhaustion during bursty traffic?
- **Event Loop Blocking Detection with BlockHound**: How does BlockHound detect hidden blocking operations on event loop threads, and how do you resolve them with `Schedulers.boundedElastic()`?
- **Spring AI Portable Architecture**: How does Spring AI abstract LLM providers (OpenAI, Anthropic Claude, Google Gemini, Ollama) via `ChatClient` and `ChatModel`?
- **Structured Output Parsing**: How does `BeanOutputConverter` generate JSON Schemas to map unstructured LLM natural language responses directly into typed Java records?
- **RAG Architecture**: Explain document chunking, embedding generation (e.g. 1536-dimensional vectors), cosine similarity search, and prompt augmentation with `VectorStore` in Spring AI.
- **Model Context Protocol (MCP)**: Explain the MCP architecture (Host, Client, Server) and how Spring AI exposes microservice methods as `@Tool` functions via JSON-RPC 2.0 over STDIO and HTTP SSE.






