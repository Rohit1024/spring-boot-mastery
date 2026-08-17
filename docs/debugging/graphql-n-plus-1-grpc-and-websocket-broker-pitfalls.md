---
icon: lucide/bug
---

# Troubleshooting GraphQL N+1, gRPC RPC & WebSocket Broker Pitfalls

Alternative communication protocols (GraphQL, gRPC, and WebSockets) operate under execution models fundamentally different from standard REST HTTP endpoints. When errors occur, standard REST exception handlers (`@RestControllerAdvice`) do not intercept them.

This playbook provides root-cause diagnostic workflows, reproducible scenarios, and verified remediation steps for GraphQL resolver query storms, gRPC channel failures, and WebSocket multi-pod message dropouts.

---

## 1. Diagnostic Decision Tree

``` mermaid
flowchart TD
    Start["Protocol Communication Failure Detected"] --> ErrType{"Identify Protocol Layer"}

    ErrType -->|Dozens of SQL queries per GraphQL request| GqlErr["1. GraphQL N+1 Query Waterfall"]
    ErrType -->|gRPC call fails with UNAVAILABLE / DEADLINE_EXCEEDED| GrpcErr["2. gRPC Channel / Port Mismatch"]
    ErrType -->|Clients on different pods do not receive messages| WsErr["3. Multi-Pod In-Memory Broker Isolation"]

    GqlErr --> FixGql["Implement @BatchMapping or register DataLoader"]
    GrpcErr --> FixGrpc["Verify grpc.client address, plaintext negotiation & deadlines"]
    WsErr --> FixWs["Replace enableSimpleBroker with enableStompBrokerRelay (RabbitMQ)"]
```

---

## 2. Issue 1: GraphQL N+1 Database Query Cascade

### Symptoms & Error Log
A single GraphQL query for 50 orders takes several seconds and floods Hibernate logs with 51 separate SQL queries:

```text
Hibernate: select o1_0.id, o1_0.total from orders o1_0 limit 50
Hibernate: select c1_0.id, c1_0.name from customers c1_0 where c1_0.id=1
Hibernate: select c1_0.id, c1_0.name from customers c1_0 where c1_0.id=2
... [Repeated 48 more times]
```

### Root Cause
Using `@SchemaMapping` on a relation field causes Spring for GraphQL to execute the resolver method once for every individual entity in the parent collection.

### Resolution
Replace individual `@SchemaMapping` resolvers with `@BatchMapping`:

```java
@BatchMapping(typeName = "Order", field = "customer")
public Map<Order, Customer> customer(List<Order> orders) {
    Set<Long> customerIds = orders.stream().map(Order::getCustomerId).collect(Collectors.toSet());
    Map<Long, Customer> customers = customerService.findByIds(customerIds);
    return orders.stream().collect(Collectors.toMap(o -> o, o -> customers.get(o.getCustomerId())));
}
```

---

## 3. Issue 2: gRPC `UNAVAILABLE` / `DEADLINE_EXCEEDED`

### Symptoms & Error Log
```text
io.grpc.StatusRuntimeException: UNAVAILABLE: io exception
Channel Pipeline: [SslHandler#0, ProtocolNegotiators$ClientTlsHandler#0, ...]
Caused by: javax.net.ssl.SSLHandshakeException: Remote host terminated the handshake
```

### Root Cause
1. **Negotiation Type Mismatch**: The client is attempting TLS/SSL handshakes (`negotiation-type: tls`) against a server configured for `plaintext`, or vice versa.
2. **Port Mismatch**: The client is querying the standard REST port (`8080`) instead of the dedicated gRPC port (`9090`).

### Diagnostic Flowchart

``` mermaid
sequenceDiagram
    autonumber
    participant Client as gRPC Client Stub
    participant Server as gRPC Netty Server (:9090)

    Client->>Server: ClientHello (TLS Handshake over Plaintext Socket)
    Server-->>Client: Connection Reset / Drop ❌
    Note over Client: Throws StatusRuntimeException: UNAVAILABLE
```

### Resolution
In client `application.yml`:

```yaml
grpc:
  client:
    order-service:
      address: 'static://localhost:9090'
      negotiation-type: plaintext # Match server SSL/Plaintext mode!
```

---

## 4. Issue 3: WebSocket Messages Not Delivered Across Clustered Pods

### Symptoms
Client A connects to `Pod 1` via WebSocket. Client B connects to `Pod 2`. When Client A sends a chat message, Client B never receives it.

### Root Cause
`registry.enableSimpleBroker("/topic")` is strictly **in-memory** within a single JVM. Messages sent to Pod 1's broker are never broadcast to Pod 2's connected clients.

### Diagnostic Flowchart

``` mermaid
sequenceDiagram
    autonumber
    actor Alice as Client A (Pod 1)
    participant Pod1 as Spring Pod 1 (In-Memory Broker)
    participant Pod2 as Spring Pod 2 (In-Memory Broker)
    actor Bob as Client B (Pod 2)

    Alice->>Pod1: SEND /app/chat (Message payload)
    Pod1->>Pod1: Broadcasts to local subscribers on Pod 1 only
    Note over Pod1,Pod2: ❌ Pod 1 cannot reach Pod 2's clients!
    Pod2--xBob: Bob receives nothing!
```

### Resolution
Replace the simple in-memory broker with a **STOMP Broker Relay** connected to RabbitMQ or ActiveMQ:

```java
@Override
public void configureMessageBroker(MessageBrokerRegistry registry) {
    registry.setApplicationDestinationPrefixes("/app");
    registry.enableStompBrokerRelay("/topic", "/queue")
            .setRelayHost("rabbitmq-cluster.default.svc.cluster.local")
            .setRelayPort(61613)
            .setClientLogin("guest")
            .setClientPasscode("guest");
}
```

---

## 🧭 Navigation & Diagnostic Playbooks

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Troubleshooting Spring Batch & Schedulers**](spring-batch-and-scheduler-locking-pitfalls.md) | [**All Debugging Guides**](index.md) | [➡️ **Spring Modulith & Virtual Threads Debugging**](spring-modulith-and-virtual-thread-pinning-pitfalls.md) |
