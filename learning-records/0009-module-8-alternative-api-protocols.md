# Learning Record 0009: Module 8 — Alternative API Protocols Completed

- **Date**: 2026-08-17
- **Module**: Module 8: Alternative API Protocols — GraphQL, gRPC & WebSockets
- **Status**: Completed

## Concepts Mastered

1. **Spring for GraphQL**:
   - Client-driven declarative querying versus REST over-fetching / under-fetching.
   - Schema-first design (`schema.graphqls`) defining types, inputs, queries, and mutations.
   - Controller mappings: `@QueryMapping`, `@MutationMapping`, and `@Argument`.
   - GraphiQL interactive testing playground configuration.

2. **GraphQL Batch Mapping & Real-Time Subscriptions**:
   - Resolving GraphQL N+1 resolver waterfalls with `@BatchMapping`, batching child entity IDs into a single `WHERE id IN (...)` query.
   - Fine-grained deferred batch loading with `DataLoader` and `BatchLoaderRegistry`.
   - Real-time event push via `@SubscriptionMapping` returning Project Reactor `Flux<T>` over WebSockets.

3. **High-Performance RPC with Spring gRPC & Protocol Buffers**:
   - Protobuf binary serialization (5-10x smaller, zero-string parsing overhead) vs REST JSON.
   - Defining service contracts with `.proto` IDL and compiling Java stubs.
   - Server implementation with `@GrpcService` and client stub injection with `@GrpcClient`.
   - Unary and server-streaming RPC communication over multiplexed HTTP/2 streams.

4. **Full-Duplex Real-Time Messaging with WebSockets & STOMP**:
   - Comparing HTTP polling, one-way Server-Sent Events (SSE), and bidirectional full-duplex WebSockets.
   - STOMP protocol frame routing (`CONNECT`, `SUBSCRIBE`, `SEND`, `MESSAGE`).
   - Configuring Spring Boot message broker with `@EnableWebSocketMessageBroker`, `@MessageMapping`, `@SendTo`, and SockJS fallback.
   - Targeted private messaging with `SimpMessagingTemplate.convertAndSendToUser()`.
   - Multi-pod horizontal scaling with external STOMP Broker Relays (RabbitMQ / ActiveMQ).

## Artifacts Produced

- Lessons: `0038`, `0039`, `0040`, `0041` (with Spring Boot 3 vs 4 comparisons and vertical Mermaid diagrams).
- Cheatsheet: `docs/cheatsheet/graphql-grpc-websockets.md`.
- Debugging Guide: `docs/debugging/graphql-n-plus-1-grpc-and-websocket-broker-pitfalls.md`.
- Interview Questions: 10 high-signal protocol questions in `docs/interview/index.md`.
- Glossary: Added definitions for GraphQL, DataLoader, Protocol Buffers, gRPC, Unary RPC, Streaming RPC, STOMP, and STOMP Broker Relay.
