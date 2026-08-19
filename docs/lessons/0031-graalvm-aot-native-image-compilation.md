---
icon: lucide/zap
---

# 0031: GraalVM AOT native image compilation

In standard JVM deployments, the HotSpot JVM executes Java bytecode via interpreters and Just-In-Time (JIT) compilers (C1/C2). While JIT compilers achieve excellent peak throughput through profile-guided optimizations, they suffer from **slow startup times (3-15 seconds)** and **heavy baseline memory consumption (200MB-500MB RSS)**.

**GraalVM Native Image** uses Ahead-Of-Time (AOT) compilation to compile your Spring Boot application, its dependencies, and a stripped-down runtime (SubstrateVM) into a **standalone, platform-native machine binary**.

In this lesson, you will master the Closed-World Assumption, understand Spring Boot's AOT processing engine, compile native binaries using `native-maven-plugin`, and author custom `RuntimeHints` for dynamic reflection.

---

## 1. JVM hotspot (JIT) vs GraalVM native image (AOT)

``` mermaid
flowchart TD
    subgraph JIT["JVM HotSpot (JIT)"]
        Source1["Java Code"] --> Bytecode1["Bytecode (.class / JAR)"]
        Bytecode1 --> JVM["JVM Startup & Classloading (3-10s)"]
        JVM --> Warmup["JIT Tiered Warm-Up (C1/C2)"]
        Warmup --> PeakJIT["Peak Performance (~300MB RAM)"]
    end

    subgraph AOT["GraalVM Native Image (AOT)"]
        Source2["Java Code"] --> SpringAOT["Spring AOT Engine (Pre-computes beans)"]
        SpringAOT --> Substrate["GraalVM Native Compiler (Closed-World Analysis)"]
        Substrate --> Binary["Native Machine Binary (ELF / Executable)"]
        Binary --> InstantBoot["Instant Boot (< 0.05s / ~35MB RAM) ⚡"]
    end

    JIT ~~~ AOT
```

### Performance operational comparison

| Metric | HotSpot JVM (JIT) | GraalVM Native Image (AOT) |
| :--- | :---: | :---: |
| **Startup Time** | $2.5\text{s} - 12.0\text{s}$ | **$0.02\text{s} - 0.08\text{s}$ (Instant)** |
| **Base Memory Footprint (RSS)** | $250\text{MB} - 600\text{MB}$ | **$30\text{MB} - 60\text{MB}$ (85% reduction)** |
| **Artifact Format** | Executable Fat JAR (~100MB) | Standalone Native Machine Binary (~40-70MB) |
| **JVM Required at Runtime?** | ✅ Yes (JRE 21+) | ❌ No (Self-contained SubstrateVM) |
| **Build Duration** | Fast (~10-30 seconds) | Slow & Memory-Heavy (~2-5 minutes, 8GB+ RAM) |
| **Ideal Architecture** | Long-running high-QPS monolithic services | **Serverless (Lambda/Cloud Run), Kubernetes Auto-Scalers, CLI Tools** |

---

## 2. The closed-world assumption Spring AOT engine

GraalVM Native Image operates under the **Closed-World Assumption**: all bytecode reachable at runtime must be known and analyzed during compilation. Any unused classes, methods, and fields are permanently stripped from the executable binary.

Because Spring traditionally relies heavily on runtime reflection, dynamic CGLIB proxies, and classpath inspection, Spring Boot 3+ introduced the **Spring AOT Processing Engine**:

``` mermaid
sequenceDiagram
    autonumber
    participant Maven as Maven / Gradle Build
    participant AOT as Spring AOT Engine
    participant CodeGen as Generated Java Source / Bytecode
    participant Graal as GraalVM native-image Compiler
    participant Output as Native ELF Binary

    Maven->>AOT: Process Application Classes & Configurations
    AOT->>AOT: Evaluates @Conditional annotations at build time
    AOT->>AOT: Resolves Bean Definitions statically
    AOT->>CodeGen: Generates static Initializers & Reflection Hints
    CodeGen->>Graal: Feeds static source + reachability-metadata.json
    Graal->>Graal: Static Reachability Analysis & Dead Code Stripping
    Graal-->>Output: Emits standalone binary (e.g. target/order-service)
```

---

## 3. Configuring native compilation with `native-maven-plugin`

Spring Boot provides first-class native compilation support via the `native` Maven profile:

### `pom.xml`
```xml
<profiles>
    <profile>
        <id>native</id>
        <build>
            <plugins>
                <plugin>
                    <groupId>org.graalvm.buildtools</groupId>
                    <artifactId>native-maven-plugin</artifactId>
                    <version>0.10.2</version>
                    <extensions>true</extensions>
                    <executions>
                        <execution>
                            <id>build-native</id>
                            <goals>
                                <goal>compile-no-fork</goal>
                            </goals>
                            <phase>package</phase>
                        </execution>
                    </executions>
                    <configuration>
                        <buildArgs>
                            <buildArg>-H:+ReportExceptionStackTraces</buildArg>
                            <buildArg>--no-fallback</buildArg> <!-- Fails if pure native cannot be built -->
                            <buildArg>--enable-http</buildArg>
                            <buildArg>--enable-https</buildArg>
                        </buildArgs>
                    </configuration>
                </plugin>
            </plugins>
        </build>
    </profile>
</profiles>
```

### Compiling and running the native binary
```bash
# 1. Compile the native binary (Requires GraalVM JDK installed locally):
mvn -Pnative clean native:compile

# 2. Run the produced machine executable:
./target/order-service
```
```text
  .   ____          _            __ _ _
 /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
 \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
  '  |____| .__|_| |_|_| |_\__, | / / / /
 =========|_|==============|___/=/_/_/_/
 :: Spring Boot ::                (v3.3.0)

2026-08-17T16:10:00.042Z  INFO --- [main] c.e.d.DemoApplication : Started DemoApplication in 0.041 seconds (process running for 0.048)
```
*(Application boots in **41 milliseconds**!)*

---

## 4. Authoring custom `RuntimeHints` for dynamic reflection

When using dynamic libraries, third-party reflection, or serialization (e.g., custom JSON parsers or dynamic Class lookup), the GraalVM static analyzer cannot infer reachability automatically.

Spring provides programmatic and declarative mechanisms to register hints:

### Option A: `@RegisterReflectionForBinding`
Place on configuration classes or records to register types for serialization/reflection:

```java
package com.example.demo.config;

import com.example.demo.dto.PaymentPayload;
import com.example.demo.dto.WebhookEvent;
import org.springframework.aot.hint.annotation.RegisterReflectionForBinding;
import org.springframework.context.annotation.Configuration;

@Configuration
@RegisterReflectionForBinding({PaymentPayload.class, WebhookEvent.class})
public class NativeHintsConfig {
    // Automatically registers constructors, fields, and methods for reflection in GraalVM!
}
```

### Option B: Custom `RuntimeHintsRegistrar`
For advanced programmatic reachability (resources, proxies, serialization):

```java
package com.example.demo.aot;

import org.springframework.aot.hint.MemberCategory;
import org.springframework.aot.hint.RuntimeHints;
import org.springframework.aot.hint.RuntimeHintsRegistrar;

public class ThirdPartyLibraryHints implements RuntimeHintsRegistrar {

    @Override
    public void registerHints(RuntimeHints hints, ClassLoader classLoader) {
        // 1. Register reflection for dynamic classes
        hints.reflection().registerType(
            org.example.legacy.DynamicPlugin.class,
            MemberCategory.INVOKE_DECLARED_CONSTRUCTORS,
            MemberCategory.INVOKE_DECLARED_METHODS
        );

        // 2. Register classpath resource files needed at runtime
        hints.resources().registerPattern("certificates/*.pem");
        hints.resources().registerPattern("graphql/**/*.graphqls");
    }
}
```

#### Register in `META-INF/spring/AOT.factories`
```properties
org.springframework.aot.hint.RuntimeHintsRegistrar=\
com.example.demo.aot.ThirdPartyLibraryHints
```

---

## 5. Spring Boot 3 vs Spring Boot 4: Native AOT evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        AOTEngine3["Spring AOT First Generation (Spring 6.0)"]
        ReachabilityRepo["External Reachability Metadata Repository"]
        ManualHints["Frequent manual @RegisterReflectionForBinding"]
    end

    subgraph SB4["Spring Boot 4.x"]
        NativeFirstEngine["Native-First Unified Compiler (Spring 7.0)"]
        AutomaticAnalysis["Deep Static Analysis of Records & Sealed Types"]
        ZeroMetadataHints["Zero-Boilerplate Reflection Registration"]
    end

    SB3 ==>|AOT Optimization| SB4
```

### Key differences and configuration comparison

| AOT & Native Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **AOT Compilation Maturity** | First-generation AOT. Required reachability metadata repository for many third-party libraries. | **Native-First AOT Pipeline**: Core frameworks and starters generate 100% of reachability metadata automatically. |
| **Record & Sealed Type Hints** | Required explicit reflection binding for deep records in REST APIs. | **Automatic Type Introspection**: Infers all record components and sealed subclasses at build time. |
| **Build-Time Memory Usage** | GraalVM native build process required 8GB-12GB of RAM. | **Optimized Build Graph**: Memory footprint during native compilation reduced by ~40%. |

---

## 6. Primary sources and further reading

- [Spring Boot Reference Guide: GraalVM Native Image Support](https://docs.spring.io/spring-boot/reference/packaging/native-image/index.html), Comprehensive native compilation documentation.
- [GraalVM Official Native Image Documentation](https://www.graalvm.org/latest/reference-manual/native-image/), Closed-world analysis, SubstrateVM, and build args.
- [GraalVM Reachability Metadata Repository](https://github.com/oracle/graalvm-reachability-metadata), Centralized community reflection hints for Java libraries.

---

## 7. Knowledge check and practice

??? question "Question 1: What is the Closed-World Assumption in GraalVM Native Image compilation?"
    **Answer**: The assumption that all classes, methods, and fields reachable by the application at runtime must be discovered and analyzed at compile-time; unreferenced code is permanently stripped.

??? question "Question 2: What role does the Spring AOT Engine play prior to GraalVM native-image execution?"
    **Answer**: It evaluates Spring bean definitions and conditions at build time, generating static Java source code and reflection hints so the container does not need runtime reflection.

??? question "Question 3: How do you register an external DTO class for reflection when using Spring Boot AOT?"
    **Answer**: By annotating a configuration class with `@RegisterReflectionForBinding(MyDto.class)` or registering a custom `RuntimeHintsRegistrar` implementation in `META-INF/spring/aot.factories`.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0030: Multi-Cloud Registry Authentication**](0030-multi-cloud-artifact-registry-authentication-jib.md) | [**All Lessons**](index.md) | [ **0032: Containerizing Native Images with Jib**](0032-containerizing-graalvm-native-images-with-jib.md) |
