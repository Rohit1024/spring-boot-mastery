---
icon: lucide/boxes
---

# 0042: Modular monoliths with Spring Modulith: DDD and boundary enforcement

For over a decade, development teams prematurely migrated from monolithic architectures to distributed microservices, only to suffer from the **"microservice tax"**: network latency, distributed transactions, deployment complexity, and high cloud infrastructure costs.

Conversely, unconstrained monoliths quickly degrade into an unmaintainable **"Big Ball of Mud"**, where arbitrary circular dependencies across packages prevent refactoring.

**Spring Modulith** enables the **Modular Monolith** pattern: structuring a single Spring Boot application into logically isolated, Domain-Driven Design (DDD) bounded contexts with strictly enforced compile-time and test-time architectural boundaries.

In this lesson, you will master Spring Modulith package conventions, enforce module encapsulation, verify structural boundaries with ArchUnit, and auto-generate living architecture documentation.

---

## 1. Monolith vs microservices vs modular monolith

``` mermaid
flowchart TD
    subgraph BallOfMud["1. Traditional Monolith (Big Ball of Mud)"]
        OrderBean["OrderService"]
        PayBean["PaymentService"]
        InvBean["InventoryService"]
        SpaghettiNote["❌ Spaghetti dependencies, no boundary encapsulation"]
        
        OrderBean <--> PayBean
        PayBean <--> InvBean
        InvBean <--> OrderBean
        PayBean --- SpaghettiNote
    end

    subgraph Microservices["2. Distributed Microservices"]
        S1["Order Pod (:8081)"]
        S2["Payment Pod (:8082)"]
        S3["Inventory Pod (:8083)"]
        NetworkTaxNote["❌ High DevOps overhead & network latency"]
        
        S1 <-->|HTTP or Kafka Network Tax| S2
        S2 <-->|HTTP or Kafka Network Tax| S3
        S2 --- NetworkTaxNote
    end

    subgraph Modulith["3. Modular Monolith (Spring Modulith)"]
        subgraph ModOrder["📦 Order Module"]
            O_API["OrderPublicAPI (Public)"]
            O_INT["OrderInternalService (Package-Private)"]
            O_API --> O_INT
        end
        
        subgraph ModPay["📦 Payment Module"]
            P_API["PaymentPublicAPI (Public)"]
            P_INT["PaymentInternalService (Package-Private)"]
            P_API --> P_INT
        end
        
        O_API -->|In-Process Event or Public API| P_API
    end

    BallOfMud ~~~ Microservices ~~~ Modulith
```

---

## 2. Spring modulith package conventions

Spring Modulith derives module boundaries directly from the Java package hierarchy under your main application class:

```text
src/main/java/com/example/ecommerce/
├── EcommerceApplication.java
├── order/                        <-- Application Module 'order'
│   ├── OrderPublicService.java   <-- Public API (Exported)
│   ├── dto/
│   │   └── OrderDto.java         <-- Public API Model
│   └── internal/                 <-- Internal Implementation (HIDDEN)
│       ├── OrderRepository.java  <-- Package-Private / Internal
│       └── OrderEntity.java
└── payment/                      <-- Application Module 'payment'
    ├── PaymentService.java       <-- Public API
    └── internal/
        └── StripeGateway.java    <-- Internal to 'payment' module
```

### Module encapsulation rules
1. **Public Packages** (directly under `order`): Accessible to other modules.
2. **Internal Packages** (`order.internal.*` or package-private classes): **Inaccessible** to other modules. If a bean in `payment` attempts to inject `OrderRepository`, Spring Modulith flags an architectural violation!

---

## 3. Verifying architectural boundaries with tests

Spring Modulith integrates with **ArchUnit** to statically analyze the entire bean and package dependency graph:

### `ModularityTests.java`
```java
package com.example.ecommerce;

import org.junit.jupiter.api.Test;
import org.springframework.modulith.core.ApplicationModules;
import org.springframework.modulith.docs.Documenter;

class ModularityTests {

    // Analyzes the application package structure from the root class
    ApplicationModules modules = ApplicationModules.of(EcommerceApplication.class);

    @Test
    void verifyModularStructure() {
        // Fails the test if any module accesses internal packages of another module!
        modules.verify();
    }

    @Test
    void createModuleDocumentation() {
        // Generates PlantUML component diagrams & AsciiDoc living architecture docs
        new Documenter(modules)
                .writeDocumentation()
                .writeModulesAsPlantUml()
                .writeIndividualFilesAsPlantUml();
    }
}
```

If an illegal cross-module import occurs:
```text
org.springframework.modulith.core.Violations: 
- Module 'payment' depends on internal component 'com.example.ecommerce.order.internal.OrderRepository'!
```

---

## 4. Explicit module interfaces (`@namedinterface` `package-info.java`)

To selectively expose specific sub-packages while keeping everything else private, use `package-info.java`:

### `src/main/java/com/example/ecommerce/order/spi/package-info.java`
```java
@org.springframework.modulith.NamedInterface("spi")
package com.example.ecommerce.order.spi;
```

Now, other modules can explicitly declare their allowed dependency in their own `package-info.java`:

### `src/main/java/com/example/ecommerce/payment/package-info.java`
```java
@org.springframework.modulith.ApplicationModule(
    allowedDependencies = "order::spi"
)
package com.example.ecommerce.payment;
```

---

## 5. Spring Boot 3 vs Spring Boot 4: Modulith evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Spring Modulith 1.1+)"]
        ArchUnitRuntime["ArchUnit Reflection Analysis"]
        PlantUmlDocs["PlantUML Component Diagrams Output"]
        StandardJvm["Standard JVM Package-Private Enforcement"]
    end

    subgraph SB4["Spring Boot 4.x (Spring Modulith 2.0)"]
        CompileTimeEnforcement["Java Compiler Plugin (Javac Boundary Errors)"]
        MermaidNativeDocs["Native Interactive Mermaid C4 Diagrams"]
        AOTModulithAnalysis["AOT Pre-Compiled Module Metamodels"]
    end

    SB3 ==>|Compile-Time Gates & AOT Tooling| SB4
```

### Key differences and configuration comparison

| Modulith Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Violation Detection** | Detected during JUnit test execution (`modules.verify()`). | **Javac Compiler Integration**: Compilation fails immediately if an internal module class is imported. |
| **Living Documentation** | Exported static PlantUML `.puml` files and AsciiDoc tables. | **Interactive C4 Mermaid Output**: Direct markdown and HTML interactive architecture dashboards. |
| **AOT / GraalVM Integration** | Required reflection configuration for dynamic event dispatchers. | **Native AOT Module Metamodels**: Zero-overhead build-time reachability resolution. |

---

## 6. Primary sources and further reading

- [Spring Modulith Reference Documentation](https://docs.spring.io/spring-modulith/reference/index.html), Official guide to module structure, verification, and documentation.
- [Oliver Drotbohm: Modularity for Spring Applications](https://spring.io/blog/2022/10/21/introducing-spring-modulith), The foundational design philosophy of Modular Monoliths.
- [Domain-Driven Design (Eric Evans)](https://www.domainlanguage.com/ddd/), Bounded contexts and ubiquitous language.

---

## 7. Knowledge check and practice

??? question "Question 1: What major operational disadvantages of microservices does a Modular Monolith eliminate?"
    **Answer**: It eliminates inter-service network latency, complex distributed transactions (SAGA/2PC), multi-repository maintenance overhead, and distributed tracing complexity while retaining clean bounded contexts.

??? question "Question 2: How does Spring Modulith distinguish between a module's public API and its internal implementation?"
    **Answer**: Classes residing in the root of the module package are public by default, while classes in nested sub-packages (e.g. `order.internal.*`) or package-private classes are treated as encapsulated internals.

??? question "Question 3: What does the `modules.verify()` test method do?"
    **Answer**: It uses ArchUnit to statically analyze the codebase, verifying that no module imports or calls internal classes from another bounded module context.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0041: WebSockets & STOMP Messaging**](0041-websockets-and-stomp-bidirectional-messaging.md) | [**All Lessons**](index.md) | [ **0043: Transactional Event Publication**](0043-transactional-event-publication-spring-modulith.md) |
