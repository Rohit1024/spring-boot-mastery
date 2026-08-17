---
icon: lucide/network
---

# GraphQL, gRPC & WebSockets Protocol Cheatsheet

A rapid reference guide for Spring for GraphQL queries, batch mapping, Protocol Buffers & gRPC RPC services, and WebSockets STOMP messaging.

---

## 1. Spring for GraphQL Quick Reference

### Schema Definition (`schema.graphqls`):
```graphql
type Query {
    order(id: ID!): Order
    orders: [Order!]!
}

type Mutation {
    createOrder(input: OrderInput!): Order!
}

type Subscription {
    orderEvents(id: ID!): OrderEvent!
}

type Order {
    id: ID!
    total: Float!
    customer: Customer!
}
```

### Controller Annotations:
```java
@Controller
public class GraphQLController {
    @QueryMapping
    public Order order(@Argument Long id) { ... }

    @MutationMapping
    public Order createOrder(@Argument OrderInput input) { ... }

    // Solves N+1 query waterfall:
    @BatchMapping(typeName = "Order", field = "customer")
    public Map<Order, Customer> customer(List<Order> orders) { ... }

    @SubscriptionMapping
    public Flux<OrderEvent> orderEvents(@Argument Long id) { ... }
}
```

---

## 2. Spring gRPC & Protocol Buffers Quick Reference

### Protobuf Definition (`order.proto`):
```protobuf
syntax = "proto3";
package order;
option java_multiple_files = true;

service OrderGrpcService {
    rpc GetOrder (OrderRequest) returns (OrderResponse);
    rpc StreamTrack (OrderRequest) returns (stream OrderStatusUpdate);
}

message OrderRequest { int64 order_id = 1; }
message OrderResponse { int64 order_id = 1; double total = 2; }
```

### Server Implementation (`@GrpcService`):
```java
@GrpcService
public class OrderGrpcServiceImpl extends OrderGrpcServiceGrpc.OrderGrpcServiceImplBase {
    @Override
    public void getOrder(OrderRequest request, StreamObserver<OrderResponse> responseObserver) {
        OrderResponse response = OrderResponse.newBuilder()
                .setOrderId(request.getOrderId())
                .setTotal(99.50)
                .build();
        responseObserver.onNext(response);
        responseObserver.onCompleted();
    }
}
```

### Client Stub Injection (`@GrpcClient`):
```java
@Service
public class OrderServiceClient {
    @GrpcClient("order-service")
    private OrderGrpcServiceBlockingStub orderStub;

    public OrderResponse fetch(long id) {
        return orderStub.withDeadlineAfter(2, TimeUnit.SECONDS)
                .getOrder(OrderRequest.newBuilder().setOrderId(id).build());
    }
}
```

---

## 3. WebSockets & STOMP Messaging Quick Reference

### Broker Configuration:
```java
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {
    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws").setAllowedOriginPatterns("*").withSockJS();
    }

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        registry.setApplicationDestinationPrefixes("/app");
        registry.enableSimpleBroker("/topic", "/queue");
        registry.setUserDestinationPrefix("/user");
    }
}
```

### Message Controller & User Notifications:
```java
@Controller
public class ChatController {
    // Broadcast to /topic/chat:
    @MessageMapping("/chat.send")
    @SendTo("/topic/chat")
    public ChatMessage broadcast(@Payload ChatMessage msg) { return msg; }
}

// Send targeted alert to a specific user:
messagingTemplate.convertAndSendToUser("alice", "/queue/notifications", alert);
```

---

## 🧭 Navigation & Cheatsheet Index

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Spring Batch & Schedulers Cheatsheet**](spring-batch-quartz-shedlock.md) | [**All Cheatsheets**](index.md) | [➡️ **Spring Modulith & Virtual Threads Cheatsheet**](spring-modulith-and-virtual-threads.md) |
