---
icon: lucide/bug
---

# Troubleshooting Jib Multi-Cloud Authentication & GraalVM Native Compilation Pitfalls

Containerizing Spring Boot applications with Google Jib and compiling native images with GraalVM introduces unique failure modes that differ fundamentally from traditional JVM and Docker CLI workflows.

This playbook provides root-cause diagnostic workflows, reproducible test scenarios, and verified remediation steps for common Jib and GraalVM native image failures.

---

## 1. Diagnostic Decision Tree

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

## 2. Issue 1: Jib `401 Unauthorized` / `403 Forbidden` on Cloud Registries

### Symptoms & Error Log
```text
[ERROR] Failed to execute goal com.google.cloud.tools:jib-maven-plugin:3.4.3:build on project order-service:
[ERROR] 401 Unauthorized
[ERROR] {"errors":[{"code":"UNAUTHORIZED","message":"authentication required"}]}
```

### Root Causes
1. The specified credential helper (e.g., `docker-credential-gcr` or `docker-credential-ecr-login`) is not installed or not available in the CI/CD runner's `$PATH`.
2. The IAM token generated via `gcloud` or `aws ecr get-login-password` expired before Jib finished uploading layers.
3. The image path prefix is malformed (e.g., omitting the repository name or region).

### Diagnostic Flowchart

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
        Registry-->>Jib: 401 Unauthorized ❌
    else Helper Succeeds
        Helper-->>Jib: Returns dynamic Bearer/Basic token
        Jib->>Registry: Authorized PUT Request
        Registry-->>Jib: 201 Created ✅
    end
```

### Resolution
1. **Verify Credential Helper in PATH**:
   ```bash
   which docker-credential-gcr
   which docker-credential-ecr-login
   ```
2. **Fallback to Direct CLI Token Injection in CI/CD**:
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

## 3. Issue 2: Native Container Crashes: `exec /app/app: no such file or directory`

### Symptoms & Error Log
When running the container produced by Jib via Docker or Kubernetes:
```text
standard_init_linux.go:228: exec user process caused: no such file or directory
# OR in Kubernetes:
CrashLoopBackOff / ContainerFailedToStart
```

### Root Cause
1. **Dynamic C-Library Mismatch**: The GraalVM native binary was dynamically compiled against `glibc`, but the Jib base image was set to `gcr.io/distroless/static-debian12` or an Alpine image (which only provides `musl` libc).
2. **Missing Executable Permissions**: The binary was copied into the container without the execute bit (`chmod +x` / `mode 755`).

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

## 4. Issue 3: GraalVM Runtime `NoSuchMethodException` / `ClassNotFoundException`

### Symptoms & Error Log
The application compiles natively without errors, but throws reflection exceptions during runtime HTTP requests:

```text
java.lang.NoSuchMethodException: com.example.dto.OrderRequest.<init>()
    at java.base@21.0.2/java.lang.Class.getConstructor0(DynamicHub.java:3762)
    at com.fasterxml.jackson.databind.deser.std.StdValueInstantiator.createUsingDefault
```

### Root Cause
Under the **Closed-World Assumption**, GraalVM eliminated constructors or methods accessed dynamically via Jackson reflection because no explicit reachability hint was registered.

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

## 5. Issue 4: CI/CD Runner Killed: `Exit Code 137` (OOMKilled)

### Symptoms & Error Log
```text
[INFO] [native-image-plugin] Compiling [order-service] to [order-service]...
/usr/bin/mvn: line 12: 14201 Killed
Process exited with code 137
```

### Root Cause
The GraalVM static analysis phase is memory-intensive and attempts to consume all available host RAM. In virtualized CI runners (GitHub Actions with 7GB RAM limit), the Linux kernel OOM-killer terminates the process.

### Resolution
Cap the GraalVM compiler's maximum heap and configure parallel thread limits in `pom.xml`:

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

## 🧭 Navigation & Diagnostic Playbooks

| ⬅️ Previous | 📋 Debugging Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Troubleshooting Security Filter Chains & JWT**](security-filter-chain-and-jwt-pitfalls.md) | [**All Debugging Guides**](index.md) | [➡️ **Spring Batch & Scheduler Troubleshooting**](spring-batch-and-scheduler-locking-pitfalls.md) |
