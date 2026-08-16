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


## ⚡ Distributed Systems & Microservices
- **SAGA vs 2PC**: Why is Two-Phase Commit anti-pattern in microservices, and how does SAGA choreography handle rollbacks via compensating transactions?
- **Transactional Outbox**: How do you guarantee zero-loss message publishing between PostgreSQL and Apache Kafka?
- **Rate Limiting**: Contrast Token Bucket vs Sliding Window Log implementation using Redis Lua scripts.
