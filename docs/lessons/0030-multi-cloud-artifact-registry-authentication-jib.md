---
icon: lucide/cloud-cog
---

# 0030: Multi-Cloud Artifact Registry Authentication & Portable Configuration with Jib

In enterprise CI/CD pipelines, hardcoding container registry URLs, credentials, or base images inside `pom.xml` is an anti-pattern that destroys build portability and creates severe security risks. A single Spring Boot service must be able to push seamlessly to **Google Cloud Artifact Registry (GAR)**, **AWS Elastic Container Registry (ECR)**, **Azure Container Registry (ACR)**, or private **Harbor / GitHub Container Registry (ghcr.io)** across dev, staging, and production environments.

In this lesson, you will master multi-cloud credential helper authentication with Jib, externalize configuration properties for 100% environment portability, and configure automated, zero-secret CI/CD pipelines.

---

## 1. Multi-Cloud Registry Authentication Architecture

Jib supports four secure authentication mechanisms in order of enterprise preference:

``` mermaid
flowchart TD
    Build["Maven / Gradle Build Engine (Jib Plugin)"] --> AuthCheck{"Authentication Lookup Order"}

    AuthCheck -->|1. Native Credential Helpers| CredHelper["Native Credential Helpers<br/>(docker-credential-gcr / ecr-login / acr-env)"]
    AuthCheck -->|2. Docker Config| DockerConfig["~/.docker/config.json<br/>(Existing CLI logins)"]
    AuthCheck -->|3. Maven settings.xml| SettingsXML["~/.m2/settings.xml<br/>(&lt;servers&gt; credentials)"]
    AuthCheck -->|4. Environment / CLI Flags| CliProps["-Djib.to.auth.username / password<br/>(CI/CD Secrets)"]

    CredHelper --> CloudRegistry["Cloud Artifact Registries<br/>(GCP GAR / AWS ECR / Azure ACR / GHCR)"]
    DockerConfig --> CloudRegistry
    SettingsXML --> CloudRegistry
    CliProps --> CloudRegistry
```

---

## 2. Cloud Provider Authentication Playbooks

### A. Google Cloud Artifact Registry / GCR

Google Cloud Artifact Registry endpoints follow the format:  
`LOCATION-docker.pkg.dev/PROJECT_ID/REPOSITORY/IMAGE_NAME:TAG`

#### Method 1: Using `docker-credential-gcr` Helper (Recommended)
```xml
<configuration>
    <to>
        <image>us-central1-docker.pkg.dev/my-gcp-project/backend-apps/order-service:${project.version}</image>
        <credHelper>gcr</credHelper>
    </to>
</configuration>
```

#### Method 2: In CI/CD with OAuth2 Access Token (GitHub Actions / GitLab CI)
In pipelines authenticated via GCP Workload Identity Federation:
```bash
# Generate short-lived OAuth2 access token
export GCP_TOKEN=$(gcloud auth print-access-token)

# Build and push with Jib:
mvn compile com.google.cloud.tools:jib-maven-plugin:build \
    -Djib.to.image=us-central1-docker.pkg.dev/my-gcp-project/backend-apps/order-service:${GIT_COMMIT} \
    -Djib.to.auth.username=oauth2accesstoken \
    -Djib.to.auth.password=$GCP_TOKEN
```

#### Method 3: Using Service Account Key File (`_json_key`)
```bash
mvn compile jib:build \
    -Djib.to.auth.username=_json_key \
    -Djib.to.auth.password="$(cat /path/to/sa-key.json)"
```

---

### B. AWS Elastic Container Registry (ECR)

AWS ECR endpoints follow the format:  
`ACCOUNT_ID.dkr.ecr.REGION.amazonaws.com/IMAGE_NAME:TAG`

#### Method 1: Using `docker-credential-ecr-login` Helper (Recommended)
```xml
<configuration>
    <to>
        <image>123456789012.dkr.ecr.us-east-1.amazonaws.com/order-service:${project.version}</image>
        <credHelper>ecr-login</credHelper>
    </to>
</configuration>
```

#### Method 2: In CI/CD with AWS CLI Temporary STS Token
```bash
# Fetch 12-hour temporary authorization token
export AWS_ECR_PASSWORD=$(aws ecr get-login-password --region us-east-1)

mvn compile jib:build \
    -Djib.to.image=123456789012.dkr.ecr.us-east-1.amazonaws.com/order-service:${GIT_COMMIT} \
    -Djib.to.auth.username=AWS \
    -Djib.to.auth.password=$AWS_ECR_PASSWORD
```

---

### C. Azure Container Registry (ACR)

Azure ACR endpoints follow the format:  
`REGISTRY_NAME.azurecr.io/IMAGE_NAME:TAG`

#### Method 1: Using `docker-credential-acr-env` Helper
```xml
<configuration>
    <to>
        <image>mycompanyacr.azurecr.io/order-service:${project.version}</image>
        <credHelper>acr-env</credHelper>
    </to>
</configuration>
```

#### Method 2: Azure Service Principal or Managed Identity
```bash
mvn compile jib:build \
    -Djib.to.image=mycompanyacr.azurecr.io/order-service:${GIT_COMMIT} \
    -Djib.to.auth.username=$AZURE_CLIENT_ID \
    -Djib.to.auth.password=$AZURE_CLIENT_SECRET
```

---

### D. GitHub Container Registry (ghcr.io) & Harbor via `settings.xml`

For standard token-based registries (GitHub Packages, Docker Hub, Harbor, Nexus):

#### `~/.m2/settings.xml`
```xml
<settings>
    <servers>
        <server>
            <id>ghcr.io</id>
            <username>github-username</username>
            <password>${env.GITHUB_TOKEN}</password>
        </server>
        <server>
            <id>registry.mycompany.internal</id>
            <username>ci-robot</username>
            <password>${env.HARBOR_ROBOT_SECRET}</password>
        </server>
    </servers>
</settings>
```
*Jib automatically matches the `<to><image>` domain with the corresponding `<server><id>` in `settings.xml`!*

---

## 3. Dynamic & Portable Configuration Architecture

To achieve complete portability across environments (local, dev cluster, staging, production cloud), externalize all image parameters into Maven properties with sensible defaults:

### `pom.xml` (Parametrized Template)
```xml
<properties>
    <!-- Default local registry / fallback -->
    <container.base-image>gcr.io/distroless/java21-debian12:nonroot</container.base-image>
    <container.registry>docker.io</container.registry>
    <container.repository>mycompany</container.repository>
    <container.image-name>${project.artifactId}</container.image-name>
    <container.tag>${project.version}</container.tag>
</properties>

<build>
    <plugins>
        <plugin>
            <groupId>com.google.cloud.tools</groupId>
            <artifactId>jib-maven-plugin</artifactId>
            <version>3.4.3</version>
            <configuration>
                <from>
                    <image>${container.base-image}</image>
                </from>
                <to>
                    <image>${container.registry}/${container.repository}/${container.image-name}:${container.tag}</image>
                </to>
                <container>
                    <mainClass>com.example.demo.DemoApplication</mainClass>
                    <creationTime>USE_CURRENT_TIMESTAMP</creationTime>
                    <jvmFlags>
                        <jvmFlag>-XX:MaxRAMPercentage=75.0</jvmFlag>
                        <jvmFlag>-XX:+ExitOnOutOfMemoryError</jvmFlag>
                    </jvmFlags>
                </container>
            </configuration>
        </plugin>
    </plugins>
</build>
```

### Overriding at Build Time across Environments:

```bash
# 1. Local Developer Build (Docker Daemon):
mvn compile jib:dockerBuild -Dcontainer.tag=local-dev

# 2. CI/CD Build to Google Cloud Artifact Registry:
mvn compile jib:build \
    -Dcontainer.registry=us-central1-docker.pkg.dev \
    -Dcontainer.repository=my-project-id/my-repo \
    -Dcontainer.tag=${GITHUB_SHA}

# 3. CI/CD Build to AWS ECR:
mvn compile jib:build \
    -Dcontainer.registry=123456789012.dkr.ecr.us-east-1.amazonaws.com \
    -Dcontainer.repository=backend \
    -Dcontainer.tag=v1.2.0
```

---

## 4. Spring Boot 3 vs Spring Boot 4: Registry & Build Automation

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        JibHelper3["Manual credHelper definitions in pom.xml"]
        ClassicProps["Maven Property Interpolation"]
        DockerSockDeps["Local Docker Socket Fallbacks"]
    end

    subgraph SB4["Spring Boot 4.x"]
        AutoCredDetect["Auto-Detected Cloud Environment Credentials"]
        OCIArtifactIndex["OCI v1.1 Artifact Manifest Indexing"]
        SigstoreCosign["Native Image Signing & SBOM Attestation"]
    end

    SB3 ==>|Supply Chain Security| SB4
```

### Key Differences & Configuration Comparison

| Registry Integration | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Credential Discovery** | Required explicit `<credHelper>` tag or CLI flags per provider. | **Automatic Ambient Credential Resolution**: Infers cloud provider identity from ambient AWS/GCP/Azure runtime context. |
| **Supply Chain Security** | Required external tools (Cosign, Syft) in pipeline to sign images and generate SBOMs. | **Native SBOM Generation**: Integrates SPDX / CycloneDX Software Bill of Materials directly into OCI image layer metadata. |
| **Multi-Architecture Tagging** | Separate tags or manual Docker manifest assembly. | **Declarative Multi-Arch Tagging**: Single OCI index tag pointing to `arm64` and `amd64` variant layers. |

---

## 5. Primary Sources & Further Reading

- [Jib Authentication Methods Documentation](https://github.com/GoogleContainerTools/jib/blob/master/docs/faq.md#what-should-i-do-when-i-get-unauthorized-401-or-forbidden-403) — Resolving authentication failures.
- [Google Cloud Artifact Registry Authentication](https://cloud.google.com/artifact-registry/docs/docker/authentication) — Setup for `docker-credential-gcr`.
- [AWS ECR Docker Credential Helper](https://github.com/awslabs/amazon-ecr-credential-helper) — IAM role-based authentication without access keys.

---

## 6. Knowledge Check & Retrieval Practice

??? question "Question 1: Why is using `docker-credential-gcr` or `docker-credential-ecr-login` superior to passing static passwords via CLI arguments in CI/CD?"
    **Answer**: Credential helpers generate short-lived, rotating OAuth2 / IAM STS tokens dynamically, preventing long-lived static secrets from being leaked in CI/CD build logs or process trees.

??? question "Question 2: How can a single `pom.xml` build configuration be made to push to any cloud registry without modifying the file?"
    **Answer**: By parameterizing the `<to><image>` block with Maven properties (e.g. `${container.registry}/${container.repository}/${project.artifactId}:${container.tag}`) and overriding them at runtime via `-D` flags.

??? question "Question 3: How does Jib authenticate with GitHub Container Registry (`ghcr.io`) when using Maven's `~/.m2/settings.xml`?"
    **Answer**: Jib matches the target registry hostname (`ghcr.io`) to the corresponding `<server><id>ghcr.io</id></server>` entry in `settings.xml` and injects the configured token.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0029: Daemonless Containerization with Jib**](0029-daemonless-containerization-google-jib.md) | [**All Lessons**](index.md) | [➡️ **0031: GraalVM AOT Native Images**](0031-graalvm-aot-native-image-compilation.md) |
