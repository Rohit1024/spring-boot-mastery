# User Learning Notes & Preferences

## Learner Profile
- **Starting Point**: Core Java & OOP concepts known; zero prior Spring experience.
- **Primary Goal**: Master Spring Boot 3.x / 4.x, Microservices, Observability (Prometheus, Grafana, OpenTelemetry), Alternative Protocols, Spring Modulith, Virtual Threads, Batch Processing, Containerization, and Distributed Systems to build production-grade projects and prepare for Senior Backend / System Design roles.
- **Teaching Strategy**: Bottom-up explanations of Spring internals (demystify annotations, reflection, proxies, and lifecycle), progressing to enterprise patterns (Prometheus, Grafana, OpenTelemetry, Spring Modulith, Virtual Threads, GraphQL, gRPC, WebSockets, Spring Batch, Quartz, ShedLock, Jib, GraalVM Native, Kafka, Redis, SAGA, Outbox, CQRS, Docker, K8s, Spring AI).

## Pedagogical Notes & Preferences
- **Mermaid Diagrams**: Always include rich Mermaid diagrams (flowcharts, sequence diagrams, state machines, component architecture) in every Lesson and Debugging guide to clearly visualize runtime behavior, execution flows, and failure modes. Use vertical spacious layouts (`flowchart TD` / vertical stacked subgraphs).
- **Zensical Navigation**: Keep `zensical.toml` sidebar clean (top-level section tabs only); maintain detailed catalogs inside each folder's `index.md`.
- **Bottom Pagination**: Every lesson, cheatsheet, and debugging guide must include a bottom navigation table linking to Previous, Catalog Index, and Next (updating adjacent files as new lessons are published).
- Keep lessons compact and high-yield with runnable code blocks, architectural diagrams, Spring Boot 3 vs 4 comparisons, and actionable quizzes/challenges.
- Track mastery with learning records.

## Masterclass Module Structure
1. **Module 1: Spring Core Fundamentals, IoC, Beans & AutoConfiguration** (Lessons 0001–0005)
2. **Module 2: RESTful Web Services, Spring MVC, DTOs & Validation** (Lessons 0006–0011)
3. **Module 3: Persistence Mastery — Hibernate ORM, Spring Data JPA & Multi-DataSource** (Lessons 0012–0017)
4. **Module 4: Observability, Logging, OpenAPI & DevTools** (Lessons 0018–0022)
5. **Module 5: Spring Security 6, OAuth2, JWT & RBAC** (Lessons 0023–0027)
6. **Module 6: Building, Packaging & Containerizing (JAR, Docker, Jib, Native Images & Cloud Registries)** (Lessons 0028–0032)
7. **Module 7: Batch Processing, Enterprise Schedulers & Distributed Locking (Spring Batch, Quartz, ShedLock)** (Lessons 0033–0037)
8. **Module 8: Alternative API Protocols (GraphQL, gRPC & WebSockets)** (Lessons 0038–0041)
9. **Module 9: Architecture Paradigms & Modern Java Features (Spring Modulith & Virtual Threads)** (Lessons 0042–0044)
10. **Module 10: Vendor-Neutral Observability (Prometheus, Grafana & OpenTelemetry)** (Lessons 0045–0047)
11. **Module 11: Enterprise Testing (JUnit 5, Mockito, Testcontainers)** (Lessons 0048–0051)
12. **Module 12: Messaging, Caching & Distributed Systems (Kafka, Redis, SAGA, Outbox, CQRS)** (Lessons 0052–0056)
13. **Module 13: Microservices, Spring Cloud, Kubernetes & Cloud CI/CD** (Lessons 0057–0071)
14. **Module 14: Reactive Programming (WebFlux) & Spring AI (LLM, RAG, MCP)** (Lessons 0072–0081)
