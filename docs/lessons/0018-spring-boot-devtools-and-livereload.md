---
icon: lucide/zap
---

# 0018: Development workflow with Spring DevTools and LiveReload

Fast feedback loops are the hallmark of high-performing engineering teams. Restarting a large Spring Boot application after every code edit wastes valuable developer time as the JVM re-indexes hundreds of third-party dependencies.

`spring-boot-devtools` eliminates this friction. In this lesson, you will dissect how DevTools achieves sub-second restarts using its **Two-ClassLoader Architecture**, configure the **Embedded LiveReload Server**, control restart triggers, and manage sensible development property overrides.

---

## 1. Why full JVM cold restarts are slow

In standard Spring Boot deployments, restarting the application forces the JVM to load thousands of external classes (Spring Core, Hibernate, Jackson, Netty, database drivers) from disk into the JVM metaspace.

``` mermaid
flowchart TD
    ColdStart["❄️ Full Cold Restart<br/>(10 - 30 seconds)"] --> Reindex["Scan & Load 5,000+ External JAR Classes"]
    Reindex --> AppContext["Initialize ApplicationContext & Beans"]
```

`spring-boot-devtools` accelerates this by splitting classes into **two isolated ClassLoaders**:

``` mermaid
flowchart TD
    subgraph JVMProcess["☕ Running JVM Process"]
        BaseCL["📦 Base ClassLoader<br/><i>(Frozen - Never Reloaded)</i><br/>Spring Boot, Hibernate, Netty, Jackson JARs"]
        
        RestartCL["⚡ Restart ClassLoader<br/><i>(Ephemeral - Discarded on Change)</i><br/>Your Custom Project Classes & Controllers"]
        
        AppCtx["🌱 ApplicationContext<br/><i>(Rebuilt in &lt; 500ms)</i>"]
    end

    BaseCL --> AppCtx
    RestartCL --> AppCtx
    
    Change["✏️ Developer edits Java File<br/>(IDE Recompiles Class)"] --> Discard["🗑️ Discard Old Restart ClassLoader<br/>Instantiate New Restart ClassLoader"]
    Discard --> RestartCL
```

### The two-classloader advantage
1. **Base ClassLoader**: Loads all external libraries from dependencies (`pom.xml` / `build.gradle`). These never change during active coding and remain permanently in memory.
2. **Restart ClassLoader**: Loads only the classes in your workspace (`target/classes` or `build/classes`). When a file changes, Spring Boot discards the small Restart ClassLoader and boots a new `ApplicationContext` in **under 500 milliseconds**.

---

## 2. Adding DevTools to your project

DevTools is strictly a development-time dependency and is automatically excluded when creating production fat JARs with `bootJar` or `spring-boot-maven-plugin`:

=== "Maven (`pom.xml`)"
    ```xml
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-devtools</artifactId>
        <scope>runtime</scope>
        <optional>true</optional>
    </dependency>
    ```

=== "Gradle (`build.gradle`)"
    ```groovy
    dependencies {
        developmentOnly 'org.springframework.boot:spring-boot-devtools'
    }
    ```

---

## 3. Automatic development property overrides

By default, production configurations enable aggressive template caching and connection pooling. DevTools automatically applies developer-friendly defaults:

| Property | Default Value | DevTools Override | Purpose |
| :--- | :--- | :--- | :--- |
| `spring.thymeleaf.cache` | `true` | `false` | Modifying HTML templates reflects immediately without restarts. |
| `spring.freemarker.cache` | `true` | `false` | Disables Freemarker view caching. |
| `spring.h2.console.enabled` | `false` | `true` | Automatically enables H2 web dashboard at `/h2-console`. |
| `spring.jpa.show-sql` | `false` | `true` | Logs generated Hibernate SQL to stdout. |
| `server.error.include-stacktrace` | `never` | `always` | Surfaces full exception traces in dev HTTP responses. |

---

## 4. LiveReload: Instant browser refresh

DevTools includes an embedded **LiveReload server** running on port `35729`. When static assets (`src/main/resources/static/`, `public/`, `templates/`) are modified, DevTools pushes a WebSocket event to your browser:

``` mermaid
sequenceDiagram
    autonumber
    actor Dev as Developer
    participant IDE as IDE / Compiler
    participant LR as DevTools LiveReload Server (:35729)
    participant Browser as Browser (LiveReload Plugin)

    Dev->>IDE: Modifies style.css or index.html
    IDE->>IDE: Compiles / Copies to target directory
    IDE->>LR: Detects resource modification
    LR->>Browser: WebSocket: { command: 'reload', path: 'style.css' }
    Browser->>Browser: Refreshes page automatically!
```

!!! tip "Browser Setup"
    Install the free **LiveReload** browser extension (available for Chrome, Firefox, and Edge) to take advantage of zero-click browser refreshes as you code.

---

## 5. Controlling restart triggers file watching

By default, whenever any compiled class changes, a restart is triggered. In fast typing sessions, this can cause multiple rapid restarts.

### Using a trigger file
You can configure DevTools to only restart when a specific trigger file is updated:

```properties
# application-dev.properties
spring.devtools.restart.trigger-file=.reloadtrigger
```
Now, Spring Boot will only restart when you touch `.reloadtrigger`:
```bash
touch .reloadtrigger
```

### Excluding static paths from restart
Static resources do not require a JVM restart, they only need a browser reload:

```properties
spring.devtools.restart.exclude=static/**,public/**,templates/**
```

---

## 6. Global developer configuration (`~/spring-boot-devtoolsproperties`)

To configure DevTools preferences across **all** Spring Boot projects on your workstation, create a file in your home directory (`~/.spring-boot-devtools.properties`):

```properties
# ~/.spring-boot-devtools.properties
spring.devtools.restart.poll-interval=1000ms
spring.devtools.restart.quiet-period=400ms
spring.devtools.livereload.enabled=true
```

---

## 7. Spring Boot 3 vs Spring Boot 4: Inner-loop tooling evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        RestartCL["Two-ClassLoader Restart Mechanism"]
        DevToolsJar["spring-boot-devtools Dependency"]
        EarlyServiceConn["Early @ServiceConnection (Boot 3.1+)"]
    end

    subgraph SB4["Spring Boot 4.x"]
        ClassFileHotSwap["Class-File API Instant Method Hot-Swap"]
        NativeDevCompose["Native Dev Compose & Testcontainers Runtime"]
        AOTDevMode["Instant AOT Local Preview Mode"]
    end

    SB3 ==>|Inner-Loop Acceleration| SB4
```

### Key differences and configuration comparison

| Developer Tooling Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Hot-Reload Architecture** | Ephemeral `RestartClassLoader` rebuilding the entire application context in ~500ms. | **Class-File API Bytecode Hot-Patching**: Swaps method bodies in-place without triggering full Spring Context teardown. |
| **Containerized Local Dev** | Optional integration via `spring-boot-docker-compose`. | **First-Class Dev Environment Management**: Automatic container bootstrapping and port auto-wiring standard. |
| **AOT Development Preview** | Required building native image binary to test AOT compliance. | **In-JVM AOT Simulation Mode**: Tests ahead-of-time bean registrations instantly inside local JVM. |

---

## 8. Primary sources and further reading

- [Spring Boot DevTools Official Reference](https://docs.spring.io/spring-boot/reference/using/devtools.html), Classloader architecture, property overrides, and remote debugging.
- [Spring Boot DevTools LiveReload Docs](https://docs.spring.io/spring-boot/reference/using/devtools.html#using.devtools.livereload), Embedded WebSocket LiveReload setup.
- [Baeldung: Spring Boot DevTools Explained](https://www.baeldung.com/spring-boot-devtools), Deep dive into automatic properties and classloader mechanics.

---

## 9. Knowledge check and practice

??? question "Question 1: Why does Spring Boot DevTools restart the application in ~500ms compared to a 15s cold boot?"
    **Answer**: It uses two ClassLoaders; third-party dependency JARs remain frozen in the Base ClassLoader, while only workspace application classes are recreated in the ephemeral Restart ClassLoader.

??? question "Question 2: Why should `spring-boot-devtools` be marked as `optional` in Maven or `developmentOnly` in Gradle?"
    **Answer**: DevTools is intended strictly for local development and must not be packaged into production artifacts where auto-restarts and developer overrides would pose security risks.

??? question "Question 3: What does the DevTools embedded LiveReload server on port 35729 do?"
    **Answer**: It notifies connected browser extensions via WebSockets to automatically refresh the web page whenever static web assets or templates are modified.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0017: Entity Auditing & Hibernate Envers**](0017-entity-auditing-and-spring-data-envers.md) | [**All Lessons**](index.md) | [ **0019: Production Health & Actuator Metrics**](0019-production-health-actuator-and-metrics.md) |
