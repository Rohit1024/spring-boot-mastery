# Learning Record 0015: Module 14 — Reactive Programming (WebFlux) & Spring AI Completed

- **Date**: 2026-08-17
- **Module**: Module 14: Reactive Programming (WebFlux) & Spring AI (Project Reactor, Schedulers, WebFlux REST/Functional, R2DBC, Reactive Redis, Server-Sent Events, Backpressure, WebTestClient, Spring AI ChatClient, Prompts, RAG Vector Stores, Model Context Protocol MCP)
- **Status**: Completed

## Concepts Mastered

1. **Blocking vs Non-Blocking I/O (0072)**:
   - Thread-per-request (Tomcat) vs Event Loop (Netty) concurrency models.
   - The Reactive Streams Specification (`Publisher`, `Subscriber`, `Subscription`, `Processor`).
   - Architectural decision matrix: Spring MVC with Virtual Threads (Java 21) vs Spring WebFlux.
   - The Golden Rule: Never block the Netty event loop thread.

2. **Project Reactor Fundamentals (0073)**:
   - `Mono<T>` (0..1 item) and `Flux<T>` (0..N items).
   - "Nothing happens until you subscribe!"
   - Operators: `map`, `flatMap`, `concatMap`, `zip`, `switchIfEmpty`, `onErrorResume`, `retryWhen(Retry.backoff())`.
   - Thread management with `Schedulers` (`boundedElastic()`, `parallel()`) and `subscribeOn` vs `publishOn`.

3. **Building Reactive REST APIs (0074)**:
   - Annotated Controllers returning `Mono<ResponseEntity<T>>` and streaming `Flux<T>` with `MediaType.APPLICATION_NDJSON_VALUE`.
   - Lightweight Functional Endpoints (`RouterFunction` and `HandlerFunction`).
   - Reactive global exception handling using `@RestControllerAdvice` and RFC 7807/9457 `ProblemDetails`.

4. **Non-Blocking Persistence with R2DBC & Reactive Redis (0075)**:
   - True non-blocking relational database access via `R2dbcRepository` and fluent `DatabaseClient`.
   - Reactive transaction management with `TransactionalOperator`.
   - Pure reactive Cache-Aside caching with `ReactiveRedisTemplate`.

5. **Real-Time Streaming with Server-Sent Events (0076)**:
   - Unidirectional real-time HTTP streaming with `MediaType.TEXT_EVENT_STREAM_VALUE` and `Flux<ServerSentEvent<T>>`.
   - Custom event IDs, named event types, browser auto-reconnection (`Last-Event-ID`), and keep-alive heartbeat pings.

6. **Reactive Backpressure Handling (0077)**:
   - Regulating fast publishers to prevent JVM heap exhaustion and OOM crashes.
   - Overflow strategies: `onBackpressureBuffer`, `onBackpressureDrop`, `onBackpressureLatest`, `onBackpressureError`.
   - Concurrency bounding on `flatMap(fn, maxConcurrency)` and rate prefetching with `limitRate`.

7. **Integration Testing Reactive APIs (0078)**:
   - Unit testing streams and simulating clock advancement using `StepVerifier` and `StepVerifier.withVirtualTime()`.
   - Reactive controller sliced testing with `@WebFluxTest` and `WebTestClient`.
   - End-to-end testing with R2DBC PostgreSQL Testcontainers and `@ServiceConnection`.

8. **Spring AI & LLM Chat Clients (0079)**:
   - Portable multi-model architecture abstracting OpenAI, Anthropic Claude, Google Gemini, and Ollama.
   - Fluent `ChatClient` builder, dynamic `PromptTemplate` parameters, and structured JSON parsing into Java records with `BeanOutputConverter`.
   - Real-time token streaming with Project Reactor `Flux<String>` via `chatClient.prompt().stream().content()`.

9. **Retrieval-Augmented Generation (RAG) & Vector Stores (0080)**:
   - Resolving LLM knowledge boundaries and hallucinations without fine-tuning.
   - Document chunking with `TokenTextSplitter`, embedding generation with `EmbeddingModel`, and storing high-dimensional vectors in PostgreSQL `pgvector`.
   - Augmenting prompts via `QuestionAnswerAdvisor` with Top-K cosine similarity search and metadata filtering.

10. **Model Context Protocol (MCP) Server & Tool Integration (0081)**:
    - The open-standard MCP architecture connecting LLMs to external tools, databases, and microservices via JSON-RPC 2.0.
    - Exposing executable tools using Spring AI `@Tool` and `java.util.function.Function` beans.
    - Exposing Spring Boot microservices as full MCP Tool Servers over STDIO and HTTP SSE transports.

## Artifacts Produced

- Lessons: `0072` through `0081` (10 lessons with vertical Mermaid diagrams and Spring Boot 3 vs 4 comparisons).
- Cheatsheet: `docs/cheatsheet/reactive-webflux-and-spring-ai.md`.
- Debugging Guide: `docs/debugging/reactive-webflux-blocking-and-spring-ai-pitfalls.md`.
- Interview Questions: 12 high-signal WebFlux, Project Reactor, and Spring AI questions in `docs/interview/index.md`.
- Glossary: Added definitions for Reactive Streams Specification, Mono, Flux, Netty Event Loop, R2DBC, Server-Sent Events (SSE), Backpressure, BlockHound, StepVerifier, Spring AI ChatClient, BeanOutputConverter, Vector Store, Embeddings, RAG, and Model Context Protocol (MCP).
- Resources: Added official R2DBC and Model Context Protocol (MCP) specification links in `docs/references/resources.md`.
