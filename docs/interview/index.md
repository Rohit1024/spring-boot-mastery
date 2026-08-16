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

## 💾 Data, Transactions & Caching
- **Transaction Propagation**: Compare `REQUIRED`, `REQUIRES_NEW`, and `NESTED` in Spring Data JPA.
- **Cache Stampede**: How do you prevent cache breakdown / stampede when using Redis caching with high concurrency?

---

## ⚡ Distributed Systems & Microservices
- **SAGA vs 2PC**: Why is Two-Phase Commit anti-pattern in microservices, and how does SAGA choreography handle rollbacks via compensating transactions?
- **Transactional Outbox**: How do you guarantee zero-loss message publishing between PostgreSQL and Apache Kafka?
- **Rate Limiting**: Contrast Token Bucket vs Sliding Window Log implementation using Redis Lua scripts.
