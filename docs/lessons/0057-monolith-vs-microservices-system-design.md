---
icon: lucide/boxes
---

# 0057: Monolith vs microservices: System design principles and service boundaries

Every architecture is an exercise in trade-offs. The monolithic architecture bundles user interface, business domain rules, background workers, and database schemas into a single deployable artifact. While simple to develop and debug initially, monoliths suffer from tight coupling, slow deployments, and organizational bottlenecks as teams scale.

**Microservices architecture** decomposes a system into loosely coupled, independently deployable, domain-driven services that communicate over lightweight network protocols (HTTP/REST, gRPC, Kafka).

In this lesson, you will master Domain-Driven Design (DDD) Bounded Contexts, Conway's Law, the Single Responsibility Principle at service boundaries, and the strategic decision matrix for choosing between Monoliths, Modular Monoliths, and Microservices.

---

## 1. Architectural paradigms: Monolith vs modular vs microservices

``` mermaid
flowchart TD
    subgraph MonolithArch["1. Monolithic Architecture"]
        MonoApp["Single Fat Application (Monolith.jar)"]
        SharedDB[("Single Shared Database (Disk Contention)")]
        MonoApp --> SharedDB
    end

    subgraph ModulithArch["2. Modular Monolith Architecture (Spring Modulith)"]
        ModApp["Single JVM Application with Enforced Module Boundaries"]
        ModOrder["Order Module"]
        ModPay["Payment Module"]
        ModInv["Inventory Module"]
        ModDB[("Unified Database with Schema Separation")]
        ModApp --> ModOrder
        ModApp --> ModPay
        ModApp --> ModInv
        ModOrder --> ModDB
        ModPay --> ModDB
        ModInv --> ModDB
    end

    subgraph MicroservicesArch["3. Microservices Architecture (Distributed)"]
        APIGateway["API Gateway"]
        OrderSvc["Order Service (Pod)"]
        PaySvc["Payment Service (Pod)"]
        InvSvc["Inventory Service (Pod)"]
        
        OrderDB[("Order DB")]
        PayDB[("Payment DB")]
        InvDB[("Inventory DB")]
        
        APIGateway --> OrderSvc
        APIGateway --> PaySvc
        APIGateway --> InvSvc
        
        OrderSvc --> OrderDB
        PaySvc --> PayDB
        InvSvc --> InvDB
    end

    MonolithArch ~~~ ModulithArch
    ModulithArch ~~~ MicroservicesArch
```

---

## 2. Core microservice design principles

### 1. Database-per-service pattern
In true microservices, **services never share a direct database**. Sharing databases introduces invisible schema coupling, database lock contention, and bypasses domain security boundaries. If Service A needs data from Service B, it must invoke Service B's API or consume domain events emitted by Service B.

### 2. Domain-driven design (DDD) bounded contexts
Identify service boundaries around distinct business capabilities (e.g. Identity, Billing, Catalog, Shipping). Within a **Bounded Context**, domain models have precise, unambiguous meanings (e.g., an `Account` in the Billing context means an invoice ledger, whereas in the Auth context it means credentials and permissions).

### 3. Conways law two-pizza teams
> *"Organizations which design systems are constrained to produce designs which are copies of the communication structures of these organizations."*, Melvin Conway

Autonomous teams of 5-8 engineers should own and operate a microservice end-to-end (code, CI/CD, database, infrastructure, alerting).

---

## 3. Monolith vs microservices trade-off matrix

| Dimension | Monolithic Architecture | Modular Monolith | Microservices Architecture |
| :--- | :--- | :--- | :--- |
| **Deployment Complexity** | Low (Single JAR/WAR to deploy). | Low (Single JAR with verified boundaries). | High (Requires Kubernetes, service mesh, CI/CD pipelines). |
| **Data Consistency** | ACID transactions across all tables. | ACID transactions within same database. | Eventual consistency (SAGA, Outbox, idempotency). |
| **Latency & Performance** | In-memory method calls (< 1µs). | In-memory method calls (< 1µs). | Network hops over HTTP/gRPC (2-50ms latency overhead). |
| **Operational Overhead** | Low (Single log file, single APM). | Moderate (In-JVM observability). | High (Distributed tracing, central logging, health meshes). |
| **Independent Scalability** | Low (Must scale whole monolith). | Low (Entire JVM scaled). | High (Scale high-traffic services independently). |
| **Team Autonomy** | Low (Merge conflicts, lockstep release).| Moderate (Module code ownership). | High (Teams deploy independently without cross-team lockstep). |

---

## 4. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Monolith-to-Microservice Migration** | Manual refactoring or Spring Modulith transition checks. | Automated architectural slicing tools and GraalVM sub-application modular boundaries. |
| **Boundary Enforcement** | ArchUnit unit tests and Spring Modulith verification. | Native compiler-enforced package isolation and zero-reflection modular runtime. |
| **Distributed Protocol Support** | Mixed HTTP/REST, OpenFeign, and Spring gRPC. | Unified declarative RPC facade with automated protocol fallback. |

---

## 5. Primary sources and further reading

- [Building Microservices (2nd Edition), Sam Newman](https://samnewman.io/books/building_microservices_2nd_edition/), The definitive guide to service boundaries, modeling, and integration.
- [Domain-Driven Design: Tackling Complexity in the Heart of Software, Eric Evans](https://www.domainlanguage.com/ddd/).
- [Microservices Patterns, Chris Richardson](https://microservices.io/), Decomposing applications, database-per-service, and distributed queries.

---

## 6. Knowledge check and practice

??? question "Question 1: Why is sharing a database across multiple microservices considered an anti-pattern?"
    **Answer**: It violates service encapsulation, creates invisible schema coupling, causes distributed locking conflicts, and prevents teams from deploying schema migrations independently.

??? question "Question 2: What is a Bounded Context in Domain-Driven Design?"
    **Answer**: A linguistic and conceptual boundary within which a domain model applies consistently, defining clear responsibilities and preventing model ambiguity.

??? question "Question 3: When should an engineering team prefer a Modular Monolith over Microservices?"
    **Answer**: When team size is small (under 20 engineers), operational complexity must remain low, and high network latency/distributed transactions cannot be justified.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0056: Rate Limiting Algorithms in Redis**](0056-redis-rate-limiting-algorithms.md) | [**All Lessons**](index.md) | [ **0058: Inter-Service Communication: Feign, WebClient & RestTemplate**](0058-interservice-communication-feign-webclient.md) |

🎉 **Lesson 0057 completed! Proceed to Lesson 0058 to master synchronous inter-service communication with OpenFeign and WebClient.**
