# Learning Record 0014: Module 13 — Microservices, Cloud & Distributed Patterns Completed

- **Date**: 2026-08-17
- **Module**: Module 13: Microservices, Cloud & Distributed Patterns (Spring Cloud, Eureka, Gateway, Config Server, Tracing, Resilience4j, SAGA, Outbox, CQRS, Idempotency, CAP, Docker, Kubernetes, AWS CI/CD)
- **Status**: Completed

## Concepts Mastered

1. **System Design & Service Boundaries (0057)**:
   - Trade-offs between Monoliths, Modular Monoliths (Spring Modulith), and Microservices.
   - Domain-Driven Design (DDD) Bounded Contexts, Conway's Law, and the Database-per-Service mandate.

2. **Inter-Service Communication (0058)**:
   - Evolution: `RestTemplate` (legacy blocking) -> `RestClient` (fluent synchronous) -> `WebClient` (reactive non-blocking) -> `Spring Cloud OpenFeign` (declarative interfaces).
   - Feign `RequestInterceptor` for JWT token/tracing propagation and custom `ErrorDecoder` for typed exception mapping.

3. **Service Discovery & Registry with Eureka (0059)**:
   - Eureka Server & Client heartbeat mechanics (`leaseRenewal`, `leaseExpiration`).
   - Self-Preservation mode defending against network partitions; Spring Cloud LoadBalancer client-side balancing.

4. **Edge Routing & Security with Spring Cloud Gateway (0060)**:
   - Reactive Netty engine architecture; Route Predicates, Gateway Filter Factories, and `GlobalFilter` chains.
   - Reactive JWT validation and header mutation (`X-User-Id`), CORS configuration, and `lb://` discovery routing.

5. **Centralized Configuration & Dynamic Bus Refresh (0061)**:
   - Spring Cloud Config Server backed by Git repositories; unified `spring.config.import` syntax.
   - Zero-downtime configuration reloads using `@RefreshScope` and Spring Cloud Bus event broadcasting via Kafka.

6. **Distributed Tracing & Correlation (0062)**:
   - Distributed Traces vs Spans; W3C `traceparent` context propagation across HTTP and Kafka.
   - Migrating from Spring Cloud Sleuth to Micrometer Tracing with OpenTelemetry bridges and Zipkin APM waterfalls.

7. **Fault Tolerance with Resilience4j (0063)**:
   - Circuit Breaker state transitions (`CLOSED` -> `OPEN` -> `HALF_OPEN`), failure rate & slow call thresholds.
   - Stacked resilience decorators (`@CircuitBreaker`, `@Retry`, `@Bulkhead`) and fallback methods.

8. **Distributed Transactions & SAGA Pattern (0064)**:
   - Replacing blocking Two-Phase Commit (2PC) with SAGA choreography over Kafka event streams.
   - Forward actions and idempotent Compensating Transactions to guarantee eventual consistency.

9. **Guaranteed Message Delivery with Transactional Outbox (0065)**:
   - Resolving the Dual-Write dilemma by persisting business aggregates and outbox events atomically in PostgreSQL.
   - High-throughput polling publishers using `FOR UPDATE SKIP LOCKED` and Debezium Change Data Capture (CDC).

10. **High-Scale Read Models with CQRS (0066)**:
    - Segregating Command (normalized 3NF write models) from Query (denormalized Elasticsearch read projections).
    - Handling asynchronous projection lag with optimistic UI updates and server push.

11. **Distributed Idempotency (0067)**:
    - Eliminating duplicate charges and events using client-provided `Idempotency-Key` headers.
    - Atomic Redis `SETNX` (`setIfAbsent`) locking with Spring AOP `@Idempotent` aspect.

12. **CAP & PACELC Theorems in Practice (0068)**:
    - Proving CP vs AP trade-offs during network partitions; analyzing PACELC (PC/EC vs PA/EL).
    - Defending financial ledgers using JPA `@Version` optimistic locking and automatic retries.

13. **Production Containerization (0069)**:
    - Hardened 3-stage Dockerfiles leveraging Spring Boot Layered JARs (`layertools`) and non-root execution.
    - Orchestrating multi-container local clusters (PostgreSQL, Kafka, Redis, Zipkin, App) with Docker Compose.

14. **Kubernetes Orchestration (0070)**:
    - Production `Deployment`, `Service`, `ConfigMap`, and `Secret` manifests.
    - Zero-downtime RollingUpdate strategies (`maxSurge: 1`, `maxUnavailable: 0`), HPA scaling, and Actuator Liveness/Readiness probes.

15. **Automated Cloud CI/CD (0071)**:
    - Multi-stage AWS CodePipeline and CodeBuild workflows with `buildspec.yml`.
    - Pushing to Amazon ECR and executing rolling zero-downtime deployments to AWS Elastic Beanstalk and ECS.

## Artifacts Produced

- Lessons: `0057` through `0071` (15 lessons with vertical Mermaid diagrams and Spring Boot 3 vs 4 comparisons).
- Cheatsheet: `docs/cheatsheet/microservices-kubernetes-and-cloud-cicd.md`.
- Debugging Guide: `docs/debugging/microservices-circuit-breaker-and-distributed-transaction-pitfalls.md`.
- Interview Questions: 15 high-signal microservices, cloud, and Kubernetes questions in `docs/interview/index.md`.
- Glossary: Added definitions for Bounded Context, Conway's Law, Database-per-Service, OpenFeign, Service Registry (Eureka), Self-Preservation Mode, API Gateway, Spring Cloud Bus, Circuit Breaker, Bulkhead Pattern, PACELC Theorem, Kubernetes Pod, Kubernetes Deployment, and Liveness vs Readiness Probe.
- Resources: Added official Spring Cloud, Resilience4j, and AWS CI/CD reference links in `docs/references/resources.md`.
