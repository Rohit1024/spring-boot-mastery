# Learning Record 0010: Module 9 — Architecture Paradigms & Modern Java Features Completed

- **Date**: 2026-08-17
- **Module**: Module 9: Architecture Paradigms & Modern Java Features (Spring Modulith & Virtual Threads)
- **Status**: Completed

## Concepts Mastered

1. **Modular Monoliths & Spring Modulith**:
   - Trading microservice operational complexity (network overhead, distributed SAGA transactions, multi-repo CI/CD) for Domain-Driven Design (DDD) modular monoliths in a single deployable artifact.
   - Module package encapsulation conventions: root public API packages versus hidden, package-private `*.internal` sub-packages.
   - Architectural boundary static analysis with ArchUnit integration via `ApplicationModules.of(App.class).verify()`.
   - Living architecture documentation generation (`Documenter`) exporting PlantUML diagrams and AsciiDoc catalogs.

2. **Transactional Event Publication & Event Registry**:
   - Decoupling inter-module communications with Domain Events (`OrderPlacedEvent`).
   - The outbox pattern within a monolith: saving domain events atomically to the `event_publication` relational table inside the originating business transaction.
   - Asynchronous, transactional event consumption using `@ApplicationModuleListener` (combining `@Async`, `@Transactional(REQUIRES_NEW)`, and `@TransactionalEventListener(AFTER_COMMIT)`).
   - Incomplete event publication recovery and replay via `IncompleteEventPublications`.

3. **Lightweight Concurrency with Java 21+ Virtual Threads (Project Loom)**:
   - Comparing 1:1 OS Platform Threads (~1MB stack, 200 Tomcat pool ceiling) with M:N user-mode Virtual Threads (~1KB stack, millions of threads).
   - Enabling Virtual Threads in Spring Boot 3.2+ and 4.x using `spring.threads.virtual.enabled=true`.
   - The unmounting and continuation lifecycle when executing blocking JDBC repository queries and HTTP calls on `ForkJoinPool` carrier threads.
   - Diagnosing and eliminating **Thread Pinning** in `synchronized` blocks using `-Djdk.tracePinnedThreads=full` and migrating to `ReentrantLock`.
   - Concurrency throttling with `Semaphore` and avoiding Virtual Thread pooling.

## Artifacts Produced

- Lessons: `0042`, `0043`, `0044` (with Spring Boot 3 vs 4 comparisons and vertical Mermaid diagrams).
- Cheatsheet: `docs/cheatsheet/spring-modulith-and-virtual-threads.md`.
- Debugging Guide: `docs/debugging/spring-modulith-and-virtual-thread-pinning-pitfalls.md`.
- Interview Questions: 10 high-signal architectural questions in `docs/interview/index.md`.
- Glossary: Added definitions for Modular Monolith, Spring Modulith, Event Publication Registry, Virtual Thread, Carrier Thread, and Thread Pinning.
