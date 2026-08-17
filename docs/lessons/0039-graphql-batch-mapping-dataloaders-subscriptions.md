---
icon: lucide/git-merge
---

# 0039: GraphQL Batch Mapping, DataLoaders & Real-Time Subscriptions

While GraphQL provides incredible frontend query flexibility, naive resolver implementations introduce catastrophic **N+1 database query waterfalls**. When resolving nested relations (e.g., retrieving the `Customer` and `Items` for 50 `Orders`), a naive field resolver executes **1 query for orders + 50 individual queries for customers**, stalling backend databases.

Furthermore, modern interactive applications require push-based, real-time updates when entities change state.

In this lesson, you will master resolving the GraphQL N+1 problem using **`@BatchMapping`**, configure asynchronous **`DataLoader`** pipelines, and stream live push events via **`@SubscriptionMapping`** over WebSockets.

---

## 1. The GraphQL N+1 Problem vs `@BatchMapping`

``` mermaid
flowchart TD
    subgraph NaiveNPlusOne["❌ Naive @SchemaMapping (N+1 Queries Waterfall)"]
        Q1["1. SELECT * FROM orders LIMIT 50 (Returns 50 orders)"]
        SubQueries["50 Individual Database Calls:<br/>SELECT * FROM customers WHERE id = 10<br/>SELECT * FROM customers WHERE id = 11<br/>...<br/>SELECT * FROM customers WHERE id = 59"]
        
        Q1 --> SubQueries
    end

    subgraph BatchMappingFix["✅ @BatchMapping / DataLoader (Single Batch Query)"]
        BQ1["1. SELECT * FROM orders LIMIT 50"]
        BQ2["2. SELECT * FROM customers WHERE id IN (10, 11, 12, ..., 59)"]
        
        BQ1 --> BQ2
    end

    NaiveNPlusOne ~~~ BatchMappingFix
```

---

## 2. Implementing `@BatchMapping` in Spring for GraphQL

`@BatchMapping` automatically intercepts field resolution across an entire list of parent entities, extracting their IDs and executing a single bulk database query:

```java
package com.example.graphql.controller;

import com.example.graphql.model.Customer;
import com.example.graphql.model.Order;
import com.example.graphql.service.CustomerService;
import org.springframework.graphql.data.method.annotation.BatchMapping;
import org.springframework.stereotype.Controller;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Controller
public class OrderFieldBatchController {

    private final CustomerService customerService;

    public OrderFieldBatchController(CustomerService customerService) {
        this.customerService = customerService;
    }

    /**
     * Resolves the 'customer' field on type 'Order' in ONE single batch query!
     * Maps to: type Order { customer: Customer! }
     */
    @BatchMapping(typeName = "Order", field = "customer")
    public Map<Order, Customer> customer(List<Order> orders) {
        // 1. Collect all unique customer IDs from the batch of orders
        Set<Long> customerIds = orders.stream()
                .map(Order::getCustomerId)
                .collect(Collectors.toSet());

        // 2. Fetch all customers in ONE SQL query: SELECT * FROM customers WHERE id IN (...)
        Map<Long, Customer> customerById = customerService.findCustomersByIds(customerIds);

        // 3. Map each parent Order back to its corresponding Customer entity
        return orders.stream()
                .collect(Collectors.toMap(
                        order -> order,
                        order -> customerById.get(order.getCustomerId())
                ));
    }
}
```

---

## 3. Asynchronous Batching with `DataLoader` & `BatchLoaderRegistry`

For cross-cutting or deeply nested multi-service scenarios, register a custom `DataLoader`:

```java
package com.example.graphql.config;

import com.example.graphql.model.Customer;
import com.example.graphql.service.CustomerService;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.graphql.execution.BatchLoaderRegistry;
import reactor.core.publisher.Mono;

import java.util.List;

@Configuration
public class DataLoaderConfig {

    @Bean
    public ApplicationRunner registerCustomerDataLoader(
            BatchLoaderRegistry registry,
            CustomerService customerService) {

        return args -> registry.forTypePair(Long.class, Customer.class)
                .registerBatchLoader((customerIds, env) -> 
                    Mono.fromCallable(() -> customerService.findCustomersOrdered(customerIds))
                );
    }
}
```

---

## 4. Real-Time Subscriptions (`@SubscriptionMapping`)

GraphQL Subscriptions allow clients to establish a persistent WebSocket connection and receive streaming push updates whenever backend events fire.

### Step 1: Update `schema.graphqls`
```graphql
type Subscription {
    orderStatusUpdates(orderId: ID!): OrderStatusPayload!
}

type OrderStatusPayload {
    orderId: ID!
    newStatus: OrderStatus!
    timestamp: String!
}
```

### Step 2: Enable WebSocket Transport in `application.yml`
```yaml
spring:
  graphql:
    websocket:
      path: /graphql
      connection-init-timeout: 60s
      keep-alive: 30s
```

### Step 3: Subscription Controller with Project Reactor `Flux<T>`
```java
package com.example.graphql.controller;

import com.example.graphql.dto.OrderStatusPayload;
import com.example.graphql.service.OrderStatusEventPublisher;
import org.springframework.graphql.data.method.annotation.Argument;
import org.springframework.graphql.data.method.annotation.SubscriptionMapping;
import org.springframework.stereotype.Controller;
import reactor.core.publisher.Flux;

@Controller
public class OrderSubscriptionController {

    private final OrderStatusEventPublisher eventPublisher;

    public OrderSubscriptionController(OrderStatusEventPublisher eventPublisher) {
        this.eventPublisher = eventPublisher;
    }

    // Maps to type Subscription { orderStatusUpdates(orderId: ID!): OrderStatusPayload! }
    @SubscriptionMapping
    public Flux<OrderStatusPayload> orderStatusUpdates(@Argument Long orderId) {
        // Returns an active reactive stream pushed over WebSocket
        return eventPublisher.getEventStreamForOrder(orderId);
    }
}
```

---

## 5. Spring Boot 3 vs Spring Boot 4: Batching & Streaming Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Spring GraphQL 1.2)"]
        ReactorFlux["Reactor Flux / Mono Execution Model"]
        StandardWs["Standard WebSocket Handler Transport"]
        ManualBatchLoader["BatchLoaderRegistry Registration"]
    end

    subgraph SB4["Spring Boot 4.x (Spring GraphQL 2.0)"]
        VirtualThreadStreams["Loom Virtual Threaded Streaming Backends"]
        Http3WebTransport["HTTP/3 WebTransport Native Bi-Directional Streams"]
        ZeroConfigDataLoader["Declarative Record DataLoaders"]
    end

    SB3 ==>|Transport Modernization & Loom Streams| SB4
```

### Key Differences & Configuration Comparison

| Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Subscription Transport** | Standard WebSockets (`/graphql` over HTTP/1.1 or HTTP/2). | **HTTP/3 WebTransport**: Multiplexed, datagram-capable low-latency streaming without TCP head-of-line blocking. |
| **DataLoader Concurrency** | CompletableFuture / Reactor Mono pipelines. | **Virtual Thread Dispatching**: Synchronous, readable repository batch lookups executed non-blockingly. |
| **Batch Loader Mapping** | Required returning `Map<Parent, Child>` or `List<Child>` with exact index alignment. | **Type-Safe Indexed Result Envelopes**: Automatic key alignment and missing key reconciliation. |

---

## 6. Primary Sources & Further Reading

- [Spring for GraphQL: Batch Loading & BatchMapping](https://docs.spring.io/spring-graphql/reference/controllers.html#controllers.batch-mapping) — Solving N+1 queries.
- [GraphQL Java DataLoader Guide](https://www.graphql-java.com/documentation/batching/) — Key caching and deferred execution.
- [Spring for GraphQL Subscriptions over WebSocket](https://docs.spring.io/spring-graphql/reference/transports.html#server.transports.websocket) — Configuring real-time reactive streams.

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: Why does a naive `@SchemaMapping` method cause an N+1 query problem when querying lists of entities?"
    **Answer**: The GraphQL engine invokes the field resolver method once for every individual entity in the parent list, executing N separate database queries instead of a single bulk query.

??? question "Question 2: How does `@BatchMapping` eliminate the N+1 query problem in Spring for GraphQL?"
    **Answer**: It intercepts the field resolution for the entire list of parent entities at once, enabling the developer to extract all keys and execute a single batch query (e.g. `WHERE id IN (...)`).

??? question "Question 3: What reactive return type is required in a `@SubscriptionMapping` controller method to push real-time events over WebSockets?"
    **Answer**: A Project Reactor `Flux<T>` (or reactive publisher) that continuously emits payload events as they occur.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0038: Spring for GraphQL**](0038-spring-graphql-schema-queries-mutations.md) | [**All Lessons**](index.md) | [➡️ **0040: Spring gRPC & Protocol Buffers**](0040-spring-grpc-and-protocol-buffers-microservices.md) |
