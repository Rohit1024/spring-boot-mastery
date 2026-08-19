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

## Packaging, Jib, Containerization & GraalVM Native

**Fat JAR (Uber JAR)**:
An executable archive containing both the compiled application classes and all packed third-party dependency JARs, loaded at runtime via Spring Boot's `JarLauncher`.

**Layered JAR (`layertools`)**:
A Spring Boot packaging format that separates an executable JAR into four distinct layers (`dependencies`, `spring-boot-loader`, `snapshot-dependencies`, `application`) to maximize Docker layer cache hits.

**Google Jib**:
A daemonless container packaging tool for Java that builds OCI and Docker-compliant container images directly from Maven or Gradle without requiring a Docker daemon or Dockerfile.

**OCI (Open Container Initiative)**:
An open governance structure defining vendor-neutral industry standards for container image formats, runtimes, and distribution specifications.

**Distroless Base Image**:
A hardened, minimal container base image provided by Google that contains only the application and its runtime dependencies (e.g. `glibc`, SSL certs) without a shell, package manager, or standard Linux utilities.

**GraalVM Ahead-Of-Time (AOT) Compilation**:
A compiler technology that translates Java bytecode into standalone machine code binaries ahead of runtime, eliminating JVM startup and warm-up latency.

**Closed-World Assumption**:
The static analysis principle in GraalVM AOT compilation requiring that all classes, methods, and fields reachable by the program at runtime be analyzed during build time, stripping any unreferenced code.

**SubstrateVM**:
The lightweight runtime embedded directly into GraalVM native binaries providing thread management, garbage collection, and memory allocation without a full JDK.

**Reachability Metadata**:
Configuration files (`reflect-config.json`, `resource-config.json`) and hints provided to GraalVM to inform the compiler about dynamic reflection, proxies, and JNI calls.

**Credential Helper**:
A standalone executable (e.g. `docker-credential-gcr`, `docker-credential-ecr-login`) that dynamically generates rotating authentication tokens for cloud container registries.

## Batch Processing, Schedulers & Distributed Locking

**JobInstance**:
A logical run of a Spring Batch job uniquely identified by its job name and identifying `JobParameters`.

**JobExecution**:
A single physical execution attempt of a `JobInstance`, tracking execution status, start time, end time, and exit code.

**Chunk-Oriented Processing**:
A streaming batch processing model where items are read and processed one-by-one and accumulated into a chunk buffer before being persisted in a single transaction commit.

**JobRepository**:
The Spring Batch persistence mechanism that manages state, checkpoints, and execution history across relational `BATCH_*` metadata tables.

**SkipPolicy**:
A fault-tolerance rule in Spring Batch determining which exceptions can be ignored during chunk execution up to a configured threshold (`skipLimit`).

**ShedLock**:
A distributed locking framework that prevents simultaneous execution of `@Scheduled` tasks across multiple instances of a microservice by acquiring an exclusive row or key lock.

**Quartz Scheduler**:
An enterprise-grade job scheduling system supporting clustered execution, persistent database triggers (`QRTZ_*`), failover recovery, and complex misfire policies.

## Alternative API Protocols (GraphQL, gRPC & WebSockets)

**GraphQL**:
An open-source data query and manipulation language for APIs providing a runtime for executing queries with existing data where the client specifies the exact response structure.

**DataLoader**:
A utility designed to solve the GraphQL N+1 problem through asynchronous batching and request-scoped memoization caching.

**Protocol Buffers (Protobuf)**:
Google's language-neutral, platform-neutral extensible binary serialization mechanism for structured data.

**gRPC**:
A high-performance, open-source universal RPC framework built on HTTP/2 multiplexing, bidirectional streaming, and Protocol Buffers.

**Unary RPC**:
A gRPC communication pattern where a client sends a single request message to the server and receives a single response message.

**Streaming RPC**:
A gRPC communication model where messages are sent in a continuous sequence over a single HTTP/2 stream (Server-Streaming, Client-Streaming, or Bidirectional).

**STOMP (Simple Text Oriented Messaging Protocol)**:
A frame-based messaging protocol providing an interoperable wire format for asynchronous messaging environments, adding destination routing over raw WebSockets.

**STOMP Broker Relay**:
A Spring WebSocket message broker component that forwards messages to and from an external message broker (such as RabbitMQ or ActiveMQ) to enable multi-node horizontal cluster scaling.

## Architecture Paradigms & Modern Java Features

**Modular Monolith**:
A software architecture style where a single unified deployable codebase is structured into strictly encapsulated, domain-driven bounded context modules with verified package boundaries.

**Spring Modulith**:
A Spring Framework project providing structural verification (via ArchUnit), transactional event outbox publication, and automated architecture documentation for modular monolith applications.

**Event Publication Registry**:
An in-monolith transactional outbox pattern implementation by Spring Modulith that persists domain events into an `event_publication` table atomically with business data to guarantee at-least-once asynchronous event delivery.

**Virtual Thread (Project Loom)**:
A lightweight user-mode thread managed directly by the Java Virtual Machine runtime (rather than the underlying OS kernel) scheduled M:N onto OS carrier threads.

**Carrier Thread**:
An underlying OS platform thread (managed by `ForkJoinPool`) that executes a Virtual Thread until the Virtual Thread reaches a blocking I/O operation and unmounts.

**Thread Pinning**:
A scenario in Project Loom where a Virtual Thread cannot unmount from its carrier thread during a blocking I/O call because execution is inside a `synchronized` block or native JNI call.

## Vendor-Neutral Observability (Prometheus, Grafana & OpenTelemetry)

**Prometheus**:
An open-source, time-series metrics monitoring and alerting system that collects metrics from configured endpoints via HTTP pull-based scraping.

**PromQL (Prometheus Query Language)**:
A functional expression language designed for real-time querying, aggregation, and mathematical calculation of dimensional time-series data.

**RED Method**:
An observability framework for request-driven services monitoring **Rate** (requests per second), **Errors** (failed requests), and **Duration** (latency distribution).

**USE Method**:
An infrastructure observability methodology analyzing **Utilization** (capacity busy time), **Saturation** (queued extra work), and **Errors** for every resource.

**OpenTelemetry (OTel)**:
A vendor-agnostic, open-source observability framework under the CNCF providing a unified set of APIs, SDKs, and tooling to generate, collect, and export telemetry data (metrics, logs, and traces).

**Span**:
The fundamental building block of a distributed trace representing a single contiguous unit of execution within a system with start time, end time, and metadata tags.

**W3C TraceContext**:
A standardized specification defining HTTP headers (`traceparent`, `tracestate`) that enable distributed tracing across heterogeneous microservices and third-party gateways.

**OTLP (OpenTelemetry Protocol)**:
A general-purpose telemetry delivery protocol defining the encoding and transport mechanisms (gRPC and HTTP/Protobuf) for traces, metrics, and logs.

## Enterprise Testing & Quality Assurance

**JUnit 5 (Jupiter)**:
The modern testing engine and annotation framework for Java applications providing lifecycle hooks, extensions, and parameterized test execution.

**AssertJ**:
A fluent, rich assertion library for Java that provides expressive, chained assertions and detailed failure diffs for complex collections and deep object hierarchies.

**Mockito**:
A popular Java mocking framework that creates dynamic bytecode proxies via ByteBuddy to stub collaborator behavior and verify method interaction contracts.

**MockMvc**:
A Spring MVC test harness that simulates HTTP requests and the full `DispatcherServlet` pipeline entirely in memory without starting a live web server or binding to a network port.

**`@WebMvcTest`**:
A Spring Boot test slice annotation that loads only the web layer (Controllers, Exception Handlers, JSON Serializers, and Filters) for high-speed integration testing.

**Testcontainers**:
A Java library that supports JUnit tests by providing lightweight, disposable Docker container instances of real databases, message brokers, and cloud services.

**`@DynamicPropertySource`**:
A Spring Test annotation used to dynamically register properties into the Spring `Environment` from external resources (such as dynamic container ports).

**`@ServiceConnection`**:
A Spring Boot 3.1+ test annotation that automatically configures container connection details (JDBC URL, credentials) into Spring auto-configurations without manual property declarations.

## High-Performance Caching & Messaging Systems

**Cache-Aside Pattern (Lazy Loading)**:
A caching pattern where the application queries the in-memory cache first, falls back to the database on a cache miss, and writes the retrieved database result into the cache for subsequent requests.

**Cache Stampede (Thundering Herd)**:
A critical failure mode occurring when a heavily queried cache key expires simultaneously, causing thousands of concurrent requests to experience a cache miss and overwhelm the primary database with identical queries.

**Cache Penetration**:
A failure scenario where queries for non-existent keys bypass the caching layer entirely and continuously hit the database; mitigated by caching empty/null values with short TTLs or using Bloom filters.

**Cache Avalanche**:
A cascading outage where large volumes of cached keys share identical TTL durations and expire at the exact same moment, flooding the database with massive batch misses; mitigated by adding random TTL jitter.

**Redis Pub/Sub**:
An ultra-fast, in-memory, fire-and-forget publish/subscribe messaging system that broadcasts messages across channels to all active subscribers without storing or retaining message history.

**Kafka Partition**:
The fundamental unit of parallelism, storage, and scalability in Apache Kafka; an append-only, immutable commit log where message ordering is strictly guaranteed.

**Consumer Group**:
A cooperative set of Kafka consumers that collectively divide and process the partitions of a topic, ensuring each partition is assigned to exactly one consumer member within the group.

**In-Sync Replicas (ISR)**:
The set of Kafka partition replica brokers that are actively caught up with the partition leader's latest Log End Offset within the configured replica lag time.

**High Watermark (HW)**:
The highest offset of a Kafka partition that has been successfully replicated across all In-Sync Replicas (ISR); records beyond the High Watermark are invisible to standard consumers.

**KRaft (Kafka Raft Metadata Mode)**:
The modern, consensus-driven metadata management subsystem in Apache Kafka that operates without external Apache ZooKeeper clusters.

**Dead Letter Topic (DLT / DLQ)**:
A dedicated message broker topic where unprocessable, malformed, or repeatedly failed records are routed after exhausting retry policies to prevent partition stalls.

**ErrorHandlingDeserializer**:
A Spring Kafka deserializer wrapper that intercepts serialization and deserialization exceptions (poison pills) in the polling loop before they can crash the consumer listener thread.

**Token Bucket Algorithm**:
A rate-limiting algorithm that maintains a bucket of tokens refilled at a constant rate up to a max capacity; allows controlled burstiness while strictly enforcing long-term average throughput.

## Distributed Systems & Microservices

**Bounded Context**:
A central pattern in Domain-Driven Design (DDD) defining a strict linguistic and conceptual boundary within which a specific domain model applies consistently.

**Conway's Law**:
The principle stating that organizations design software architectures that mirror their internal communication and team structures.

**Database-per-Service**:
An architectural pattern where each microservice owns and encapsulates its private datastore, strictly prohibiting external services from direct database access.

**OpenFeign**:
A declarative HTTP client library developed by Netflix and maintained in Spring Cloud that synthesizes HTTP request dispatchers from annotated Java interfaces.

**Service Registry (Eureka)**:
A dynamic phonebook service where microservice instances register their hostnames, IP addresses, and ports upon startup to help client-side load balancing.

**Self-Preservation Mode**:
A protection mechanism in Eureka Server that halts instance eviction when heartbeat failure rates spike unexpectedly, preventing healthy instances from being purged during network partitions.

**API Gateway**:
A reverse-proxy entry point that encapsulates internal microservice network topology, routes client traffic, and enforces cross-cutting policies (authentication, SSL, rate limiting, and CORS).

**Spring Cloud Bus**:
An event-driven communication backbone linking distributed Spring Boot nodes over Kafka or RabbitMQ to broadcast state events (such as `/actuator/busrefresh`).

**Circuit Breaker**:
A resilience design pattern that wraps remote calls and monitors failure rates, transitioning between `CLOSED`, `OPEN`, and `HALF_OPEN` states to prevent cascading thread pool exhaustion.

**Bulkhead Pattern**:
An isolation pattern that partitions system compute resources (thread pools or semaphore permits) into bounded pools so a failure in one downstream dependency cannot crash the entire service.

**Idempotency**:
A property of an operation whereby performing it multiple times yields the exact same outcome as performing it once.

**Outbox Pattern**:
A distributed pattern where database changes and corresponding integration events are written atomically into a local outbox table before being published to a message broker.

**SAGA Pattern**:
A sequence of local transactions across microservices coordinated either by choreography (events) or orchestration (central coordinator) to maintain eventual consistency.

**CQRS (Command Query Responsibility Segregation)**:
An architectural pattern that separates read and update operations into distinct models to optimize performance, scaling, and security.

**PACELC Theorem**:
An extension of the CAP theorem stating that in a distributed system, if there is a partition (P), one must trade off availability (A) and consistency (C); else (E), one must trade off latency (L) and consistency (C).

**Kubernetes Pod**:
The smallest deployable compute unit in Kubernetes, encapsulating one or more tightly coupled containers sharing network IP and storage volumes.

**Kubernetes Deployment**:
A declarative controller that manages the desired state, replica counts, rolling updates, and rollbacks for a set of Pods.

**Liveness vs Readiness Probe**:
A Liveness Probe checks if an application container is alive and restarts it if frozen, whereas a Readiness Probe verifies if the application is ready to accept incoming traffic.

## 🚀 Reactive Programming & Spring AI

**Reactive Streams Specification**:
A standard for asynchronous stream processing with non-blocking backpressure, defined by four core interfaces: `Publisher`, `Subscriber`, `Subscription`, and `Processor`.

**Mono**:
A Project Reactor reactive type that emits at most one element (0 or 1) before terminating with an `onComplete` or `onError` signal.

**Flux**:
A Project Reactor reactive type that emits an asynchronous sequence of 0 to N elements (or an infinite stream) before completing.

**Netty Event Loop**:
A non-blocking, asynchronous execution model where a tiny pool of worker threads (typically 1 per CPU core) multiplexes thousands of concurrent TCP socket connections using Linux `epoll` or macOS `kqueue`.

**R2DBC (Reactive Relational Database Connectivity)**:
An open specification and set of non-blocking database drivers enabling pure reactive stream integration with relational SQL databases (PostgreSQL, MySQL, SQL Server).

**Server-Sent Events (SSE)**:
A W3C standard protocol (`text/event-stream`) for unidirectional, real-time streaming from server to client over standard HTTP with native browser auto-reconnection.

**Backpressure**:
A flow-control mechanism in reactive streams where a slow consumer explicitly requests capacity from a fast producer (`Subscription.request(n)`), preventing memory exhaustion and OOM crashes.

**BlockHound**:
A byte-code instrumentation tool designed to detect blocking method calls (such as JDBC or thread sleeps) on non-blocking reactive event loop threads.

**StepVerifier**:
A test harness from `reactor-test` that subscribes to a reactive publisher and asserts the exact sequence of emitted items, timeouts, virtual time steps, and terminal signals.

**Spring AI ChatClient**:
A fluent, high-level API in Spring AI providing a unified interface to query LLMs across multiple providers (OpenAI, Claude, Gemini, Ollama) with prompt templates and advisors.

**BeanOutputConverter**:
A Spring AI utility that uses JSON Schema reflection to instruct LLMs to format natural language output into structured JSON, automatically mapping responses into Java records.

**Vector Store (Vector DB)**:
A specialized database engine (e.g. PostgreSQL `pgvector`, Qdrant, Pinecone) optimized for indexing and executing nearest-neighbor similarity searches across high-dimensional numerical vectors.

**Embeddings**:
High-dimensional numerical array representations of text, audio, or images generated by an embedding model that capture semantic meaning and contextual relationships.

**RAG (Retrieval-Augmented Generation)**:
An AI architecture that retrieves relevant contextual document snippets from a vector database and injects them into an LLM prompt to eliminate hallucinations and supply proprietary domain knowledge.

**Model Context Protocol (MCP)**:
An open standard created by Anthropic that connects AI models to external tools, database resources, and executable microservice capabilities via standardized JSON-RPC 2.0 messages.
