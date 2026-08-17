---
icon: lucide/package
---

# 0028: Packaging Paradigms: Fat JAR vs Layered JAR vs Multi-Stage Dockerfile

In modern cloud and Kubernetes environments, how you package your Spring Boot application directly dictates your CI/CD pipeline build speed, container registry bandwidth consumption, startup latency, and container attack surface.

Spring Boot revolutionized Java packaging with the self-contained **Fat JAR (Uber JAR)**. However, deploying monolithic 100MB+ Fat JARs inside standard Docker containers creates severe caching inefficiencies. In this lesson, you will master the internal mechanics of Spring Boot's `JarLauncher`, understand **Layered JARs** with `jarmode=layertools`, construct production-grade multi-stage Dockerfiles, choose the optimal minimal base image, and configure container JVM ergonomics.

---

## 1. Fat JAR Mechanics: `JarLauncher` & Nested Archives

Standard Java `java.exe` classloaders cannot load classes from nested JAR files inside a parent JAR archive. Spring Boot solves this via its custom loader architecture in `spring-boot-maven-plugin` / `spring-boot-gradle-plugin`:

``` mermaid
flowchart TD
    subgraph FatJAR["Spring Boot Executable Fat JAR (app.jar)"]
        Manifest["META-INF/MANIFEST.MF<br/>Main-Class: JarLauncher<br/>Start-Class: com.example.Application"]
        Loader["org/springframework/boot/loader/**<br/>(Custom ClassLoader Engine)"]
        BootInf["BOOT-INF/"]
        
        subgraph BootInfStructure["BOOT-INF Content"]
            Classes["classes/<br/>(Your Compiled .class & application.yml)"]
            Lib["lib/<br/>(Embedded 3rd-party JARs: spring-core, tomcat, jackson...)"]
            ClasspathIndex["classpath.idx<br/>(Deterministic load order)"]
            LayersIndex["layers.idx<br/>(Layer mapping metadata)"]
        end
        
        BootInf --> BootInfStructure
    end

    Manifest --> Loader
    Loader -->|Explodes virtual classpath & invokes| Classes
    Loader -->|Extracts & binds| Lib

    FatJAR ~~~ BootInfStructure
```

### Manifest Header Configuration
When you run `java -jar app.jar`, the JVM executes `org.springframework.boot.loader.launch.JarLauncher`, which establishes the `LaunchedURLClassLoader` and delegates execution to your application's actual `@SpringBootApplication` `Start-Class`.

```properties
Manifest-Version: 1.0
Main-Class: org.springframework.boot.loader.launch.JarLauncher
Start-Class: com.example.demo.DemoApplication
Spring-Boot-Version: 3.3.0
Spring-Boot-Classes: BOOT-INF/classes/
Spring-Boot-Lib: BOOT-INF/lib/
Spring-Boot-Classpath-Index: BOOT-INF/classpath.idx
Spring-Boot-Layers-Index: BOOT-INF/layers.idx
```

---

## 2. The Docker Caching Problem with Fat JARs

When deploying via standard Dockerfiles, copying the entire `app.jar` as a single layer forces Docker to invalidate and re-upload the entire 120MB layer on every 1-line code commit:

``` mermaid
flowchart TD
    subgraph Inefficient["❌ Naive Dockerfile (Single Layer Invalidation)"]
        Base1["Base OS Layer (~200MB) [Cached]"]
        FatLayer["COPY app.jar (120MB) [💥 INVALIDATED EVERY COMMIT!]"]
        Base1 --> FatLayer
    end

    subgraph Efficient["✅ Layered JAR (Surgical Layer Caching)"]
        Base2["Base OS Layer (~200MB) [Cached]"]
        DepLayer["dependencies (85MB) [Cached - 90 days]"]
        LoaderLayer["spring-boot-loader (1MB) [Cached - 90 days]"]
        SnapLayer["snapshot-dependencies (15MB) [Cached - 7 days]"]
        AppLayer["application code (2MB) [💥 ONLY 2MB RE-UPLOADED!]"]
        
        Base2 --> DepLayer --> LoaderLayer --> SnapLayer --> AppLayer
    end

    Inefficient ~~~ Efficient
```

---

## 3. Spring Boot Layered JARs (`layertools`)

Spring Boot automatically generates `BOOT-INF/layers.idx`, classifying files into four distinct layers sorted by change frequency:

1. **`dependencies`**: Static third-party release JARs (Spring, Jackson, Hibernate). *Changes rarely.*
2. **`spring-boot-loader`**: The internal Spring Boot launcher classes. *Changes rarely.*
3. **`snapshot-dependencies`**: Internal multi-module snapshot libraries. *Changes occasionally.*
4. **`application`**: Your project classes, compiled controllers, and `application.yml`. *Changes on every commit.*

### Extracting Layers with `jarmode`
```bash
# Inspect available layers:
java -Djarmode=layertools -jar target/app.jar list

# Extract layers into separate folders:
java -Djarmode=layertools -jar target/app.jar extract
```

---

## 4. Production Multi-Stage Dockerfile

A production-grade Dockerfile uses a multi-stage build to compile, extract layers, and run the container under an unprivileged non-root user with minimal attack surface:

```dockerfile
# ==========================================
# Stage 1: Extraction Stage
# ==========================================
FROM eclipse-temurin:21-jre-jammy AS extractor
WORKDIR /extracted
ARG JAR_FILE=target/*.jar
COPY ${JAR_FILE} app.jar
RUN java -Djarmode=layertools -jar app.jar extract

# ==========================================
# Stage 2: Minimal Hardened Runtime
# ==========================================
FROM eclipse-temurin:21-jre-jammy AS runtime
WORKDIR /application

# 1. Create unprivileged security user (UID 10001)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# 2. Copy layers in order of least-frequently changed to most-frequently changed
COPY --from=extractor --chown=appuser:appgroup /extracted/dependencies/ ./
COPY --from=extractor --chown=appuser:appgroup /extracted/spring-boot-loader/ ./
COPY --from=extractor --chown=appuser:appgroup /extracted/snapshot-dependencies/ ./
COPY --from=extractor --chown=appuser:appgroup /extracted/application/ ./

# 3. Switch to non-root user
USER appuser:appgroup

# 4. Container JVM ergonomics & port exposure
EXPOSE 8080 8081
ENV JAVA_OPTS="-XX:MaxRAMPercentage=75.0 -XX:+UseG1GC -XX:+ExitOnOutOfMemoryError"

# 5. Launch directly via JarLauncher (Instant start without jar unzipping)
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS org.springframework.boot.loader.launch.JarLauncher"]
```

---

## 5. Base Image Matrix & Security Trade-Offs

| Base Image | Size (Uncompressed) | Shell & Package Manager | Vulnerability Risk (CVE) | Recommended Use |
| :--- | :---: | :---: | :---: | :--- |
| **`eclipse-temurin:21-jre-jammy`** | ~220 MB | `bash`, `apt` | Medium | Standard enterprise default (easy debugging). |
| **`eclipse-temurin:21-alpine`** | ~140 MB | `sh`, `apk` (musl libc) | Low | Lightweight (warning: DNS/musl compatibility). |
| **`gcr.io/distroless/java21-debian12`** | ~170 MB | ❌ None (No shell, no package manager) | **Minimal** | **High-security production workloads**. |
| **`cgr.dev/chainguard/jre:latest`** | ~160 MB | ❌ Zero-CVE minimal | **Near Zero** | Enterprise zero-CVE compliance policies. |

---

## 6. Spring Boot 3 vs Spring Boot 4: Packaging Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        JarLauncher3["JarLauncher package: org.springframework.boot.loader.launch.JarLauncher"]
        LayerTools3["jarmode=layertools extraction"]
        DockerBuilds["Standard Dockerfile / Cloud Native Buildpacks"]
    end

    subgraph SB4["Spring Boot 4.x"]
        JarLauncher4["Modularized Lightweight Launcher"]
        JarmodeTools["jarmode=tools (Unified AOT & Layer Extraction)"]
        NativeOCI["Direct Native OCI Layer Output"]
    end

    SB3 ==>|Packaging Streamlining| SB4
```

### Key Differences & Configuration Comparison

| Packaging Feature | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Launcher Package Name** | Moved to `org.springframework.boot.loader.launch.JarLauncher` (in Boot 3.2+). | **Unified Modular Launcher**: Streamlined classpath discovery engine with Class-File API optimizations. |
| **Layer Tools Mode** | `java -Djarmode=layertools -jar app.jar extract`. | **`java -Djarmode=tools -jar app.jar extract`**: Unified tool mode for layer extraction and AOT metadata validation. |
| **Virtual Thread Ergonomics** | Required manual `-XX:+UnlockDiagnosticVMOptions` tuning for older kernels. | **Loom Runtime Optimized**: Auto-configures thread carrier pools based on CPU cgroups v2 limits. |

---

## 7. Primary Sources & Further Reading

- [Spring Boot Reference Guide: Layering Docker Images](https://docs.spring.io/spring-boot/reference/packaging/container-images/dockerfiles.html) — Official documentation on layer extraction.
- [Google Container Tools: Distroless Images](https://github.com/GoogleContainerTools/distroless) — Hardened container base images without package managers.
- [Java Virtual Machine Container Ergonomics](https://docs.oracle.com/en/java/javase/21/troubleshoot/troubleshoot-jvm-docker.html) — Managing cgroups memory limits and JVM heap sizing.

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: Why does copying a monolithic Fat JAR into a Docker container negate Docker layer caching benefits?"
    **Answer**: Any code change invalidates the entire single JAR layer, forcing CI/CD runners and container registries to re-build and re-upload all 100MB+ of unchanged third-party dependencies.

??? question "Question 2: What are the four default layers created by Spring Boot's `layers.idx`?"
    **Answer**: `dependencies` (third-party releases), `spring-boot-loader` (launcher code), `snapshot-dependencies` (internal project modules), and `application` (classes and resources).

??? question "Question 3: Why is `-XX:MaxRAMPercentage=75.0` preferred over fixed heap sizes (`-Xmx2g`) in container environments?"
    **Answer**: It dynamically sizes the JVM maximum heap relative to the container's allocated memory limits in Kubernetes / Docker cgroups, avoiding container OOMKilled crashes when limits change.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0027: Google OAuth2 & OIDC**](0027-google-oauth2-and-openid-connect-oidc.md) | [**All Lessons**](index.md) | [➡️ **0029: Daemonless Containerization with Jib**](0029-daemonless-containerization-google-jib.md) |
