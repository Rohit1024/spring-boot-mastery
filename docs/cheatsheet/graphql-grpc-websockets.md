---
icon: lucide/network
---

# GraphQL, gRPC, and WebSockets protocol cheatsheet

Reference for Spring for GraphQL queries, batch mapping, Protocol Buffers, gRPC RPC services, and WebSockets STOMP messaging.

---

## 1. Spring for GraphQL quick reference

### Schema definition (`schema.graphqls`)
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

### Controller annotations
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

## 2. Spring gRPC and Protocol Buffers quick reference

### Protobuf definition (`order.proto`)
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

### Server implementation (`@GrpcService`)
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

### Client stub injection (`@GrpcClient`)
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

## 3. WebSockets and STOMP messaging quick reference

### Broker configuration
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

### Message controller and user notifications
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

## Navigation and cheatsheet index

| Previous | Cheatsheet index | Next |
| :--- | :---: | ---: |
| [**Spring Batch and schedulers cheatsheet**](spring-batch-quartz-shedlock.md) | [**All cheatsheets**](index.md) | [**Spring Modulith and virtual threads cheatsheet**](spring-modulith-and-virtual-threads.md) |
