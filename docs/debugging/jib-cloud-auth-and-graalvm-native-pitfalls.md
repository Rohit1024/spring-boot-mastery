---
icon: lucide/bug
---

# Troubleshooting Jib multi-cloud authentication and GraalVM native compilation pitfalls

Containerizing Spring Boot applications with Google Jib and compiling native images with GraalVM introduces failure modes that differ from traditional JVM and Docker CLI workflows.

Here are root-cause diagnostic workflows, test scenarios, and remediation steps for common Jib and GraalVM native image failures.

---

## 1. Diagnostic decision tree

``` mermaid
flowchart TD
    Start["Containerization / Native Build Failure"] --> ErrType{"Identify Failure Stage"}

    ErrType -->|Jib Push Fails with 401 / 403| JibAuth["1. Cloud Registry Authentication Error"]
    ErrType -->|Container crashes: 'no such file or directory'| LibcErr["2. glibc / Base Image Mismatch"]
    ErrType -->|Native Binary throws NoSuchMethodException| ReflectionErr["3. Missing GraalVM Reachability Hint"]
    ErrType -->|CI Runner Killed with Exit Code 137| OomErr["4. Native Compiler RAM Exhaustion"]

    JibAuth --> FixJib["Verify Credential Helper in PATH / Refresh Token"]
    LibcErr --> FixLibc["Use gcr.io/distroless/base-debian12 & Set mode 755"]
    ReflectionErr --> FixReflection["Add @RegisterReflectionForBinding or RuntimeHints"]
    OomErr --> FixOom["Add -J-Xmx6g to native build args or swap space"]
```

---

## 2. Issue 1: Jib `401 Unauthorized` / `403 Forbidden` on cloud registries

### Symptoms
```text
[ERROR] Failed to execute goal com.google.cloud.tools:jib-maven-plugin:3.4.3:build on project order-service:
[ERROR] 401 Unauthorized
[ERROR] {"errors":[{"code":"UNAUTHORIZED","message":"authentication required"}]}
```

### Root causes
1. The specified credential helper (`docker-credential-gcr` or `docker-credential-ecr-login`) is not installed or not available in the CI/CD runner's `$PATH`.
2. The IAM token generated via `gcloud` or `aws ecr get-login-password` expired before Jib finished uploading layers.
3. The image path prefix is malformed (such as omitting the repository name or region).

### Diagnostic flowchart

``` mermaid
sequenceDiagram
    autonumber
    participant Jib as Jib Plugin
    participant Helper as docker-credential-gcr / ecr
    participant Registry as Cloud Artifact Registry

    Jib->>Helper: Request auth token for us-central1-docker.pkg.dev
    alt Helper Not in PATH or Not Configured
        Helper-->>Jib: Command Not Found / Empty Output
        Jib->>Registry: Anonymous PUT Request
        Registry-->>Jib: 401 Unauthorized
    else Helper Succeeds
        Helper-->>Jib: Returns dynamic Bearer/Basic token
        Jib->>Registry: Authorized PUT Request
        Registry-->>Jib: 201 Created
    end
```

### Resolution
1. **Verify credential helper in PATH**:
   ```bash
   which docker-credential-gcr
   which docker-credential-ecr-login
   ```
2. **Inject CLI tokens directly in CI/CD**:
   ```bash
   # For Google Cloud:
   mvn compile jib:build \
     -Djib.to.auth.username=oauth2accesstoken \
     -Djib.to.auth.password="$(gcloud auth print-access-token)"

   # For AWS ECR:
   mvn compile jib:build \
     -Djib.to.auth.username=AWS \
     -Djib.to.auth.password="$(aws ecr get-login-password --region us-east-1)"
   ```

---

## 3. Issue 2: Native container crashes: `exec /app/app: no such file or directory`

### Symptoms
When running the container produced by Jib via Docker or Kubernetes:
```text
standard_init_linux.go:228: exec user process caused: no such file or directory
# OR in Kubernetes:
CrashLoopBackOff / ContainerFailedToStart
```

### Root causes
1. **Dynamic C library mismatch**: The GraalVM native binary was dynamically compiled against `glibc`, but the Jib base image was set to `gcr.io/distroless/static-debian12` or an Alpine image (which only provides `musl` libc).
2. **Missing executable permissions**: The binary was copied into the container without the execute bit (`mode 755`).

### Resolution
In your `pom.xml` Jib configuration:

```xml
<configuration>
    <!-- 1. Use base-debian12 (contains glibc), NOT static-debian12 -->
    <from>
        <image>gcr.io/distroless/base-debian12:nonroot</image>
    </from>
    <extraDirectories>
        <paths>
            <path>
                <from>${project.build.directory}</from>
                <into>/app</into>
                <includes><include>${project.artifactId}</include></includes>
            </path>
        </paths>
        <!-- 2. Explicitly set execute permissions (755) -->
        <permissions>
            <permission>
                <file>/app/${project.artifactId}</file>
                <mode>755</mode>
            </permission>
        </permissions>
    </extraDirectories>
    <container>
        <entrypoint>
            <arg>/app/${project.artifactId}</arg>
        </entrypoint>
    </container>
</configuration>
```

---

## 4. Issue 3: GraalVM runtime `NoSuchMethodException` / `ClassNotFoundException`

### Symptoms
The application compiles natively without errors, but throws reflection exceptions during runtime HTTP requests:

```text
java.lang.NoSuchMethodException: com.example.dto.OrderRequest.<init>()
    at java.base@21.0.2/java.lang.Class.getConstructor0(DynamicHub.java:3762)
    at com.fasterxml.jackson.databind.deser.std.StdValueInstantiator.createUsingDefault
```

### Root cause
Under the closed-world assumption, GraalVM eliminates constructors or methods accessed dynamically via Jackson reflection because no explicit reachability hint was registered.

### Resolution
Register the DTO class with Spring Boot AOT:

```java
package com.example.demo.config;

import com.example.demo.dto.OrderRequest;
import com.example.demo.dto.OrderResponse;
import org.springframework.aot.hint.annotation.RegisterReflectionForBinding;
import org.springframework.context.annotation.Configuration;

@Configuration
@RegisterReflectionForBinding({OrderRequest.class, OrderResponse.class})
public class NativeReflectionConfig {
}
```

---

## 5. Issue 4: CI/CD runner killed: `Exit Code 137` (OOMKilled)

### Symptoms
```text
[INFO] [native-image-plugin] Compiling [order-service] to [order-service]...
/usr/bin/mvn: line 12: 14201 Killed
Process exited with code 137
```

### Root cause
The GraalVM static analysis phase consumes substantial RAM. In virtualized CI runners with strict limits (GitHub Actions with 7GB RAM limit), the Linux kernel OOM killer terminates the process.

### Resolution
Cap the GraalVM compiler maximum heap and configure parallel thread limits in `pom.xml`:

```xml
<configuration>
    <buildArgs>
        <!-- Limit compiler heap to 5GB to prevent runner OOM -->
        <buildArg>-J-Xmx5g</buildArg>
        <!-- Reduce compilation threads from 8 to 2 -->
        <buildArg>-H:NumberOfThreads=2</buildArg>
        <buildArg>--no-fallback</buildArg>
    </buildArgs>
</configuration>
```

---

## Navigation and debugging index

| Previous | Debugging index | Next |
| :--- | :---: | ---: |
| [**Troubleshooting security filter chains and JWT**](security-filter-chain-and-jwt-pitfalls.md) | [**All debugging guides**](index.md) | [**Spring Batch and scheduler troubleshooting**](spring-batch-and-scheduler-locking-pitfalls.md) |
