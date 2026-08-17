---
icon: lucide/cpu
---

# 0032: Containerizing GraalVM Native Images with Google Jib & Distroless

Compiling a Spring Boot application with GraalVM produces a standalone native Linux executable binary. However, to deploy this binary onto modern orchestration platforms like **Kubernetes**, **Google Cloud Run**, or **AWS ECS**, the executable must be packaged into an OCI-compliant container image.

While many developers default to multi-stage Dockerfiles, building GraalVM inside a Docker container requires allocating 8GB+ of memory to the Docker daemon and slows down CI/CD pipelines.

In this lesson, you will master the **Hybrid Jib + GraalVM Pipeline**: compiling the native binary on your build runner and using **Google Jib to package and publish microscopic (~45MB) Distroless native container images without Docker**.

---

## 1. The Architecture: GraalVM + Jib Hybrid Pipeline

``` mermaid
flowchart TD
    subgraph Step1["Step 1: GraalVM AOT Compilation (Runner)"]
        Source["Java 21+ Source Code"] --> SpringAOT["Spring AOT Engine"]
        SpringAOT --> GraalCompiler["native-maven-plugin (GraalVM)"]
        GraalCompiler --> Binary["target/order-service<br/><i>(Standalone Linux ELF Executable ~45MB)</i>"]
    end

    subgraph Step2["Step 2: Jib Daemonless Containerization"]
        Binary --> ExtraDirs["Jib extraDirectories (/app/order-service)"]
        DistrolessBase["gcr.io/distroless/base-debian12:nonroot<br/><i>(Minimal glibc + SSL CA certs ~25MB)</i>"] --> JibEngine["Jib Container Assembly (In-Memory)"]
        ExtraDirs --> JibEngine
    end

    subgraph Step3["Step 3: Direct Registry Push"]
        JibEngine --> RemoteRegistry["Remote Artifact Registry<br/>(GCP GAR / AWS ECR / Azure ACR)"]
    end

    Step1 ~~~ Step2 ~~~ Step3
```

### Key Advantages of Jib for Native Binaries:
1. **No Docker Daemon Required**: The CI runner compiles the native binary and Jib uploads the OCI image directly to your registry over HTTP/2.
2. **Minimal Distroless Footprint**: Total container size is only **~45MB to ~70MB** (compared to 250MB+ for standard JVM containers).
3. **Reproducible Layering**: Base OS layer (glibc/certs) remains cached; only the native binary layer updates on code changes.

---

## 2. Choosing the Native Base Image

Because GraalVM dynamic native binaries link against the standard C library (`glibc`), the container base image must supply `glibc` and root SSL certificates:

| Base Image | Size | Included Libraries | Shell? | Security Level |
| :--- | :---: | :--- | :---: | :--- |
| **`gcr.io/distroless/base-debian12:nonroot`** *(Recommended)* | ~25 MB | `glibc`, `libssl`, `ca-certificates` | ❌ No | **Highest (OWASP Golden Standard)** |
| **`gcr.io/distroless/static-debian12:nonroot`** | ~3 MB | Minimal static libraries only (Requires `--static` musl build) | ❌ No | Extreme Minimalist |
| **`alpine:3.20`** | ~8 MB | `musl` libc (Requires `gcompat` or static GraalVM build) | `sh` | Low (Compatibility overhead) |

---

## 3. Configuring Maven for Jib Native Packaging

Configure a dedicated Maven profile that pairs `native-maven-plugin` with `jib-maven-plugin`:

### `pom.xml`
```xml
<profiles>
    <!-- Profile for GraalVM Native Compilation + Jib Packaging -->
    <profile>
        <id>native-jib</id>
        <properties>
            <container.base-image>gcr.io/distroless/base-debian12:nonroot</container.base-image>
            <container.registry>us-central1-docker.pkg.dev/my-gcp-project/backend-apps</container.registry>
            <container.image-name>${project.artifactId}</container.image-name>
            <container.tag>${project.version}</container.tag>
        </properties>
        <build>
            <plugins>
                <!-- 1. GraalVM Native Compiler -->
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
                        <imageName>${project.artifactId}</imageName>
                        <buildArgs>
                            <buildArg>--no-fallback</buildArg>
                            <buildArg>-H:+ReportExceptionStackTraces</buildArg>
                        </buildArgs>
                    </configuration>
                </plugin>

                <!-- 2. Google Jib Daemonless OCI Packager -->
                <plugin>
                    <groupId>com.google.cloud.tools</groupId>
                    <artifactId>jib-maven-plugin</artifactId>
                    <version>3.4.3</version>
                    <configuration>
                        <from>
                            <image>${container.base-image}</image>
                        </from>
                        <to>
                            <image>${container.registry}/${container.image-name}:${container.tag}</image>
                        </to>
                        <!-- Inject the compiled native binary into /app/ -->
                        <extraDirectories>
                            <paths>
                                <path>
                                    <from>${project.build.directory}</from>
                                    <into>/app</into>
                                    <includes>
                                        <include>${project.artifactId}</include>
                                    </includes>
                                </path>
                            </paths>
                            <permissions>
                                <!-- Grant executable permissions to the binary -->
                                <permission>
                                    <file>/app/${project.artifactId}</file>
                                    <mode>755</mode>
                                </permission>
                            </permissions>
                        </extraDirectories>
                        <container>
                            <!-- Override entrypoint to launch native executable directly -->
                            <entrypoint>
                                <arg>/app/${project.artifactId}</arg>
                            </entrypoint>
                            <ports>
                                <port>8080</port>
                                <port>8081</port>
                            </ports>
                            <user>nonroot:nonroot</user>
                            <creationTime>USE_CURRENT_TIMESTAMP</creationTime>
                        </container>
                    </configuration>
                </plugin>
            </plugins>
        </build>
    </profile>
</profiles>
```

---

## 4. Execution & Pipeline Automation

### 1. Local / CI Execution Command
```bash
# Compiles native binary and pushes container directly to cloud registry:
mvn clean package jib:build -Pnative-jib
```

### 2. Complete GitHub Actions CI/CD Pipeline (`.github/workflows/native-jib.yml`)

```yaml
name: Build & Push Native Container

on:
  push:
    branches: [ main ]

jobs:
  build-native-jib:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up GraalVM JDK 21
        uses: graalvm/setup-graalvm@v1
        with:
          java-version: '21'
          distribution: 'graalvm-community'
          github-token: ${{ secrets.GITHUB_TOKEN }}
          cache: 'maven'

      - name: Build Native Image and Publish with Jib
        run: |
          mvn clean package jib:build -Pnative-jib \
            -Dcontainer.registry=ghcr.io/${{ github.repository_owner }} \
            -Dcontainer.tag=${{ github.sha }} \
            -Djib.to.auth.username=${{ github.actor }} \
            -Djib.to.auth.password=${{ secrets.GITHUB_TOKEN }}
```

---

## 5. Startup & Footprint Benchmark in Production

Once deployed to Kubernetes or Google Cloud Run:

```bash
docker run -p 8080:8080 ghcr.io/mycompany/order-service:v1.0.0
```

```text
2026-08-17T16:10:45.021Z  INFO 1 --- [main] c.e.d.DemoApplication : Started DemoApplication in 0.038 seconds (process running for 0.042)
```

| Deployment Metric | Standard JVM Container | GraalVM + Jib Container | Improvement Factor |
| :--- | :---: | :---: | :---: |
| **Total Container Image Size** | ~280 MB | **~48 MB** | **83% smaller** |
| **Startup Latency** | 6.2 seconds | **0.038 seconds** | **160x faster** |
| **Idle Memory (RSS)** | 340 MB | **32 MB** | **90% reduction** |
| **Vulnerability Count (CVE)** | 12-25 | **0** | **100% clean** |

---

## 6. Spring Boot 3 vs Spring Boot 4: Native Container Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        ManualExtraDirs["Manual extraDirectories Maven XML Configuration"]
        GlibcRequired["glibc Base Distroless Binding"]
        BuildTime8GB["8GB-12GB CI Runner Memory Ceiling"]
    end

    subgraph SB4["Spring Boot 4.x"]
        NativeJibPlugin["Native-Aware Jib Plugin Extensions"]
        StaticMuslNative["Static Musl Native Packaging (Scratch Base ~35MB)"]
        StreamlinedAOTMem["4GB Low-Memory Native Compilation"]
    end

    SB3 ==>|Native Packaging Convergence| SB4
```

### Key Differences & Configuration Comparison

| Native Container Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Jib Native Configuration** | Required manual `<extraDirectories>` mapping and entrypoint override. | **Native-Aware Jib Auto-Packaging**: Jib automatically recognizes native binary build targets. |
| **Static Scratch Containers** | Challenging due to glibc dynamic linker dependencies. | **Fully Static Musl Binary Support**: Runs on `scratch` (0MB OS base) for absolute minimum surface. |
| **Multi-Arch Compilation** | Required cross-compiler toolchains or QEMU emulators on x86 CI runners. | **Target Architecture Matrix**: Simplified cross-compilation for ARM64 Graviton / Apple Silicon. |

---

## 7. Primary Sources & Further Reading

- [GoogleContainerTools Jib: Extra Directories Documentation](https://github.com/GoogleContainerTools/jib/blob/master/docs/faq.md#how-do-i-add-extra-files-to-the-image) — Setting custom file permissions and entrypoints.
- [GraalVM Native Image with Distroless Guide](https://github.com/GoogleContainerTools/distroless) — Running native executables in minimal Linux distributions.
- [Cloud Native Computing Foundation: MicroVM & Serverless Containers](https://www.cncf.io/) — Best practices for sub-second scaling.

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: Why is `gcr.io/distroless/base-debian12` used instead of `gcr.io/distroless/java21` when containerizing GraalVM native images with Jib?"
    **Answer**: The GraalVM native binary is already compiled machine code that embeds SubstrateVM; it does not need a Java Runtime Environment (JRE), but requires standard C library dependencies (`glibc` and SSL certs) provided by `base-debian12`.

??? question "Question 2: How does Jib's `<extraDirectories>` configuration place the native binary into the container image?"
    **Answer**: It copies files from the local target directory (`${project.build.directory}`) directly into the container filesystem (e.g. `/app/order-service`) and applies the specified Unix file permissions (`mode 755`).

??? question "Question 3: What entrypoint configuration must be specified in Jib when running a native image executable?"
    **Answer**: The `<entrypoint>` must be explicitly configured with the path to the native executable (`<arg>/app/order-service</arg>`), overriding Jib's default Java class execution.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0031: GraalVM AOT Native Images**](0031-graalvm-aot-native-image-compilation.md) | [**All Lessons**](index.md) | [➡️ **0033: Spring Batch Core Architecture**](0033-spring-batch-architecture-jobrepository.md) |

🎉 **Congratulations on completing Module 6: Building, Packaging & Containerizing Spring Boot Applications!**
