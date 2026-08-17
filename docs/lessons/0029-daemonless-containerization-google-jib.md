---
icon: lucide/container
---

# 0029: Daemonless Containerization with Google Jib (Maven & Gradle)

Building container images with a traditional `docker build` command requires running a full Docker daemon on your build machine or CI/CD runner. In Kubernetes-based CI/CD pipelines (e.g., Tekton, GitLab CI, GitHub Actions, Jenkins on K8s), running Docker requires mounting the host's privileged Docker socket (`/var/run/docker.sock`) or running insecure Docker-in-Docker (DinD) with root privileges.

**Google Jib** revolutionizes Java containerization by building optimized OCI and Docker-compliant container images **directly from Maven or Gradle without needing a Docker daemon or Dockerfile**.

In this lesson, you will master Jib's internal architecture, configure `jib-maven-plugin` and `jib-gradle-plugin`, leverage intelligent layer caching, and configure reproducible container builds.

---

## 1. Traditional Docker Daemon vs Google Jib Architecture

``` mermaid
flowchart TD
    subgraph DockerWay["❌ Traditional Docker Build Workflow"]
        D1["Compile Java Code (JAR)"] --> D2["Execute 'docker build' CLI"]
        D2 --> D3["Docker Daemon (Root Privileges Required)"]
        D3 --> D4["Pulls Base Image to Local Disk"]
        D4 --> D5["Executes Dockerfile Steps"]
        D5 --> D6["Pushes Layers to Remote Registry"]
    end

    subgraph JibWay["✅ Google Jib Workflow (Daemonless)"]
        J1["Compile Java Classes & Dependencies"] --> J2["Jib Plugin (Inside Maven / Gradle JVM)"]
        J2 --> J3["Reads Remote Registry Manifest Directly"]
        J3 --> J4["Constructs OCI Layers & Hashes in Memory"]
        J4 --> J5["Uploads ONLY Changed Layer Blobs via HTTP/2"]
        J5 --> J6["Updates Image Manifest in Registry"]
    end

    DockerWay ~~~ JibWay
```

### Why Jib Outperforms Dockerfiles in CI/CD:
1. **Daemonless**: No Docker CLI, no Docker daemon, no root socket required.
2. **Deterministic & Reproducible**: Generates bit-identical images when source code has not changed.
3. **Bandwidth Efficient**: Jib computes cryptographic SHA-256 layer hashes locally and only transfers the layers that don't already exist on the target container registry.
4. **Fast**: Splits code into multiple layers automatically without needing multi-stage Dockerfiles or `jarmode=layertools` extraction.

---

## 2. Jib's Automatic 4-Layer Architecture

Jib analyzes your build classpath and automatically arranges your container into four distinct OCI layers:

``` mermaid
flowchart TD
    subgraph BaseImage["Base Image (e.g. gcr.io/distroless/java21-debian12)"]
        OS["Linux Minimal Runtime & OpenJDK"]
    end

    subgraph JibLayers["Jib Application Layers (Ordered by Change Frequency)"]
        L1["1. Dependencies Layer<br/><code>/app/libs/spring-boot-*.jar</code><br/><i>(Changes rarely - Highly cached)</i>"]
        L2["2. Snapshot Dependencies Layer<br/><code>/app/libs/*-SNAPSHOT.jar</code><br/><i>(Changes when internal modules update)</i>"]
        L3["3. Resources Layer<br/><code>/app/resources/application.yml</code><br/><i>(Config files, message bundles)</i>"]
        L4["4. Classes Layer<br/><code>/app/classes/com/example/**/*.class</code><br/><i>(Your compiled Java classes - ~200KB)</i>"]
    end

    BaseImage --> L1 --> L2 --> L3 --> L4
```

When you edit a single REST controller:
- Jib rebuilds **only Layer 4** (a tiny ~200KB delta).
- Layers 1, 2, and 3 are 100% cached on both your build machine and the remote registry.
- Build and push time drops from **45 seconds to < 2 seconds**!

---

## 3. Configuring `jib-maven-plugin` in `pom.xml`

Add `jib-maven-plugin` to your `<build><plugins>` block:

```xml
<plugin>
    <groupId>com.google.cloud.tools</groupId>
    <artifactId>jib-maven-plugin</artifactId>
    <version>3.4.3</version>
    <configuration>
        <!-- 1. Base Image Configuration -->
        <from>
            <image>gcr.io/distroless/java21-debian12:nonroot</image>
        </from>
        
        <!-- 2. Target Registry & Tags -->
        <to>
            <image>docker.io/mycompany/order-service:${project.version}</image>
            <tags>
                <tag>latest</tag>
                <tag>${git.commit.id.abbrev}</tag>
            </tags>
        </to>
        
        <!-- 3. Container Runtime Environment -->
        <container>
            <mainClass>com.example.demo.DemoApplication</mainClass>
            <jvmFlags>
                <jvmFlag>-XX:MaxRAMPercentage=75.0</jvmFlag>
                <jvmFlag>-XX:+UseG1GC</jvmFlag>
                <jvmFlag>-XX:+ExitOnOutOfMemoryError</jvmFlag>
                <jvmFlag>-Djava.security.egd=file:/dev/./urandom</jvmFlag>
            </jvmFlags>
            <ports>
                <port>8080</port>
                <port>8081</port>
            </ports>
            <user>nonroot:nonroot</user>
            <creationTime>USE_CURRENT_TIMESTAMP</creationTime>
            <format>OCI</format> <!-- or Docker -->
        </container>
    </configuration>
</plugin>
```

---

## 4. Jib Execution Goals

Jib provides three primary Maven/Gradle goals:

``` mermaid
flowchart TD
    M["mvn compile"] --> G1["jib:build<br/><i>(Direct to Registry without Docker)</i>"]
    M --> G2["jib:dockerBuild<br/><i>(Direct to local Docker daemon for local dev)</i>"]
    M --> G3["jib:buildTar<br/><i>(Exports tarball image to disk for air-gapped systems)</i>"]
```

### 1. Build and Push Directly to Remote Registry (CI/CD)
```bash
mvn compile jib:build
```
*(Does NOT require Docker installed on the CI runner!)*

### 2. Build Directly into Local Docker Daemon (Local Dev)
```bash
mvn compile jib:dockerBuild
```
*(Requires local Docker running; immediately available via `docker images` and `docker run`).*

### 3. Export as Tarball (Air-Gapped / Security Scanning)
```bash
mvn compile jib:buildTar
# Generates target/jib-image.tar loadable via 'docker load --input target/jib-image.tar'
```

---

## 5. Gradle DSL Configuration (`build.gradle.kts`)

For Kotlin Gradle builds:

```kotlin
plugins {
    id("com.google.cloud.tools.jib") version "3.4.3"
}

jib {
    from {
        image = "gcr.io/distroless/java21-debian12:nonroot"
    }
    to {
        image = "docker.io/mycompany/order-service:${project.version}"
        tags = setOf("latest")
    }
    container {
        mainClass = "com.example.demo.DemoApplication"
        jvmFlags = listOf("-XX:MaxRAMPercentage=75.0", "-XX:+UseG1GC")
        ports = listOf("8080", "8081")
        user = "nonroot:nonroot"
        creationTime.set("USE_CURRENT_TIMESTAMP")
    }
}
```

```bash
# Gradle command to build and push:
./gradlew jib
```

---

## 6. Spring Boot 3 vs Spring Boot 4: Jib & OCI Packaging

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        JibPlugin["jib-maven-plugin 3.4.x"]
        Distroless21["Distroless Java 21 Base Image"]
        CloudPaketo["Spring Boot build-image (Paketo Cloud Native Buildpacks)"]
    end

    subgraph SB4["Spring Boot 4.x"]
        JibModern["Jib Multi-Platform Manifest Support"]
        Distroless25["Distroless Java 25 & Chainguard Minimal"]
        NativeOCIEngine["Native-First OCI Layout with Instant Class-File Index"]
    end

    SB3 ==>|Containerization Modernization| SB4
```

### Key Differences & Configuration Comparison

| Containerization Aspect | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Default Base Image Target** | `gcr.io/distroless/java17-debian11` or `java21-debian12`. | **`gcr.io/distroless/java21-debian12` or Java 25 Minimal**. |
| **Multi-Architecture Support** | Required `<platforms><platform>` configuration in Jib for `linux/amd64` and `linux/arm64`. | **Automatic Multi-Arch OCI Indexing**: Seamless manifest list generation for Apple Silicon and x86_64 cloud nodes. |
| **Spring Boot Cloud Native Buildpacks vs Jib** | `mvn spring-boot:build-image` uses Paketo/Docker daemon. | **Jib Daemonless Advantage**: Jib remains 5x faster in K8s pipelines because it avoids launching builder containers. |

---

## 7. Primary Sources & Further Reading

- [GoogleContainerTools Jib Official GitHub Repository](https://github.com/GoogleContainerTools/jib) — Complete configuration parameter reference.
- [Jib Maven Plugin Documentation](https://github.com/GoogleContainerTools/jib/tree/master/jib-maven-plugin) — System properties, authentication, and execution lifecycle.
- [Google Cloud Open Source: Container Best Practices with Jib](https://cloud.google.com/java/getting-started/jib) — Optimizing layer cache utilization.

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: Why does Google Jib NOT require a Dockerfile or Docker daemon to build a container image?"
    **Answer**: Jib directly packages compiled class files and dependencies into standard OCI layer tarballs and communicates directly with the remote container registry API over HTTP/2.

??? question "Question 2: What happens if you do not set `<creationTime>USE_CURRENT_TIMESTAMP</creationTime>` in Jib?"
    **Answer**: Jib defaults the image creation timestamp to Unix Epoch 0 (`1970-01-01T00:00:00Z`) to ensure reproducible, deterministic byte-for-byte image hashes.

??? question "Question 3: Which Jib goal builds the container image and registers it with the local Docker daemon for local testing?"
    **Answer**: The `jib:dockerBuild` Maven goal (or `jibDockerBuild` in Gradle).

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0028: Packaging Paradigms (JAR & Docker)**](0028-packaging-paradigms-jar-docker-layering.md) | [**All Lessons**](index.md) | [➡️ **0030: Multi-Cloud Registry Authentication**](0030-multi-cloud-artifact-registry-authentication-jib.md) |
