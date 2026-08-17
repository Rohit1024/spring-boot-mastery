---
icon: lucide/network
---

# 0038: Spring for GraphQL: Schema Design, Queries, Mutations & GraphiQL

While REST APIs have been the de facto standard for web services, they suffer from two major client integration bottlenecks: **over-fetching** (retrieving 50 fields when the client UI only needs 2) and **under-fetching** (requiring 4 sequential HTTP requests to assemble a single mobile view).

**Spring for GraphQL** (built on `GraphQL Java`) provides a first-class, schema-first programming model that allows clients to declare the exact shape and fields of data they need in a single request.

In this lesson, you will master GraphQL schema design (`schema.graphqls`), map queries and mutations using `@QueryMapping` and `@MutationMapping`, test with GraphiQL, and handle input arguments and validation.

---

## 1. REST vs GraphQL Architectural Paradigm

``` mermaid
flowchart TD
    subgraph RESTModel["1. REST API Model (Server Dictates Shape)"]
        ClientREST["Client UI"]
        Endpoint1["GET /api/v1/orders/42 (Returns 40 order fields)"]
        Endpoint2["GET /api/v1/customers/10 (Returns 25 customer fields)"]
        Endpoint3["GET /api/v1/products/99 (Returns 30 product fields)"]
        
        ClientREST -->|1. Request Order| Endpoint1
        ClientREST -->|2. Request Customer| Endpoint2
        ClientREST -->|3. Request Product| Endpoint3
    end

    subgraph GraphQLModel["2. GraphQL Model (Client Dictates Shape)"]
        ClientGQL["Client UI"]
        SingleEndpoint["POST /graphql (Single Request)"]
        QueryPayload["query { order(id: 42) { totalAmount customer { email } items { name price } } }"]
        
        ClientGQL -->|Sends declarative query| SingleEndpoint
        SingleEndpoint -->|Returns tailored JSON matching query| QueryPayload
    end

    RESTModel ~~~ GraphQLModel
```

---

## 2. Schema-First Design (`schema.graphqls`)

In Spring for GraphQL, the contract is strictly defined in `src/main/resources/graphql/schema.graphqls`:

```graphql
# 1. Root Query Operations
type Query {
    orderById(id: ID!): Order
    allOrders(limit: Int = 10, offset: Int = 0): [Order!]!
    searchProducts(keyword: String!): [Product!]!
}

# 2. Root Mutation Operations
type Mutation {
    createOrder(input: CreateOrderInput!): Order!
    cancelOrder(id: ID!): Boolean!
}

# 3. Domain Types
type Order {
    id: ID!
    orderNumber: String!
    status: OrderStatus!
    totalAmount: Float!
    createdAt: String!
    customer: Customer!
    items: [OrderItem!]!
}

type Customer {
    id: ID!
    fullName: String!
    email: String!
}

type OrderItem {
    id: ID!
    productName: String!
    quantity: Int!
    unitPrice: Float!
}

type Product {
    id: ID!
    name: String!
    sku: String!
    price: Float!
}

enum OrderStatus {
    PENDING
    PAID
    SHIPPED
    CANCELLED
}

# 4. Mutation Input Types
input CreateOrderInput {
    customerId: ID!
    itemIds: [ID!]!
}
```

---

## 3. Spring Boot Controller Mappings (`@QueryMapping` & `@MutationMapping`)

Spring Boot binds schema fields directly to controller methods matching the schema operation name:

### `OrderGraphQLController.java`
```java
package com.example.graphql.controller;

import com.example.graphql.dto.CreateOrderInput;
import com.example.graphql.model.Order;
import com.example.graphql.service.OrderService;
import org.springframework.graphql.data.method.annotation.Argument;
import org.springframework.graphql.data.method.annotation.MutationMapping;
import org.springframework.graphql.data.method.annotation.QueryMapping;
import org.springframework.stereotype.Controller;

import java.util.List;
import java.util.Optional;

@Controller
public class OrderGraphQLController {

    private final OrderService orderService;

    public OrderGraphQLController(OrderService orderService) {
        this.orderService = orderService;
    }

    // Maps to type Query { orderById(id: ID!): Order }
    @QueryMapping
    public Optional<Order> orderById(@Argument Long id) {
        return orderService.findOrderById(id);
    }

    // Maps to type Query { allOrders(limit: Int, offset: Int): [Order!]! }
    @QueryMapping
    public List<Order> allOrders(@Argument int limit, @Argument int offset) {
        return orderService.findAllOrders(limit, offset);
    }

    // Maps to type Mutation { createOrder(input: CreateOrderInput!): Order! }
    @MutationMapping
    public Order createOrder(@Argument CreateOrderInput input) {
        return orderService.createOrder(input);
    }

    // Maps to type Mutation { cancelOrder(id: ID!): Boolean! }
    @MutationMapping
    public boolean cancelOrder(@Argument Long id) {
        return orderService.cancelOrder(id);
    }
}
```

---

## 4. GraphiQL Interactive IDE & Configuration

Spring Boot provides the **GraphiQL** browser IDE for interactive query authoring, schema exploration, and documentation inspection.

### `application.yml`
```yaml
spring:
  graphql:
    graphiql:
      enabled: true
      path: /graphiql
    schema:
      printer:
        enabled: true
      locations: classpath:graphql/**/
    cors:
      allowed-origins: "*"
      allowed-methods: GET,POST
```

Navigate to `http://localhost:8080/graphiql` to execute queries with autocompletion:

```graphql
# Sample Query in GraphiQL:
query GetOrderDetails {
  orderById(id: "42") {
    orderNumber
    status
    totalAmount
    customer {
      fullName
      email
    }
    items {
      productName
      quantity
      unitPrice
    }
  }
}
```

---

## 5. Spring Boot 3 vs Spring Boot 4: GraphQL Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Spring GraphQL 1.2)"]
        AnnotationMap["@QueryMapping & @MutationMapping"]
        JavaBeanDTOs["JavaBean Input Classes"]
        StandardTransport["HTTP POST / WebSockets Transport"]
    end

    subgraph SB4["Spring Boot 4.x (Spring GraphQL 2.0)"]
        RecordGraphQL["Java Record Automatic Schema Derivation"]
        VirtualThreadResolvers["Virtual-Thread Native Concurrent Resolvers"]
        AOTSchemaCompiler["AOT Pre-Compiled GraphQL Document ASTs"]
    end

    SB3 ==>|Schema Modernization & Loom Resolvers| SB4
```

### Key Differences & Configuration Comparison

| GraphQL Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Input Arguments Mapping** | Required standard POJOs with getters and setters. | **Java Record Input Mapping**: Maps GraphQL input objects directly to immutable records with canonical constructors. |
| **Field Execution Threading** | Platform thread pool for data fetching resolvers. | **Virtual Thread Dispatching**: Executes independent field resolvers concurrently on lightweight Loom threads. |
| **Document Parsing Overhead** | Parses query strings into ASTs dynamically per HTTP request. | **AOT Pre-Compiled Query Hashes**: Caches compiled ASTs across client queries for 4x faster execution. |

---

## 6. Primary Sources & Further Reading

- [Spring for GraphQL Official Reference Documentation](https://docs.spring.io/spring-graphql/reference/index.html) — Core architecture, controllers, schema mapping, and GraphiQL setup.
- [GraphQL Official Specification](https://spec.graphql.org/) — Type system, execution algorithm, and validation rules.
- [GraphQL Java Documentation](https://www.graphql-java.com/documentation/overview/) — Low-level engine powering Spring for GraphQL.

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the fundamental difference between over-fetching in REST and declarative fetching in GraphQL?"
    **Answer**: Over-fetching occurs when a fixed REST endpoint returns large payloads containing unnecessary fields; GraphQL lets the client explicitly specify only the exact subset of fields required.

??? question "Question 2: How does Spring Boot automatically link a controller method to a field in `schema.graphqls`?"
    **Answer**: By matching the controller method name annotated with `@QueryMapping` or `@MutationMapping` to the corresponding query or mutation field name defined in the schema.

??? question "Question 3: What annotation is used to extract query arguments or mutation input payloads inside a `@QueryMapping` method?"
    **Answer**: The `@Argument` annotation (e.g. `@Argument Long id` or `@Argument CreateOrderInput input`).

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0037: Quartz Scheduler & ShedLock**](0037-quartz-scheduler-and-shedlock-distributed-locking.md) | [**All Lessons**](index.md) | [➡️ **0039: Batch Mapping & Subscriptions**](0039-graphql-batch-mapping-dataloaders-subscriptions.md) |
