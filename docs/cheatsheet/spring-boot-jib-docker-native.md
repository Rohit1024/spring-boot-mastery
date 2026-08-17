---
icon: lucide/container
---

# Spring Boot Packaging, Jib & GraalVM Native Cheatsheet

A rapid reference guide for Spring Boot multi-stage Dockerfiles, Google Jib daemonless container builds, multi-cloud registry authentication commands, and GraalVM AOT native image compilation.

---

## 1. Spring Boot Layered JAR Commands

```bash
# 1. Inspect internal layers inside the executable JAR
java -Djarmode=layertools -jar target/app.jar list

# 2. Extract layers into separate folders (dependencies, loader, snapshot-dependencies, application)
java -Djarmode=layertools -jar target/app.jar extract

# 3. Launch extracted application directly via JarLauncher
java -XX:MaxRAMPercentage=75.0 org.springframework.boot.loader.launch.JarLauncher
```

---

## 2. Google Jib CLI Quick Reference

```bash
# Direct push to remote registry (No Docker daemon needed)
mvn compile jib:build \
  -Djib.to.image=us-central1-docker.pkg.dev/my-gcp-project/apps/order-service:v1.0.0

# Build directly to local Docker daemon (for local testing)
mvn compile jib:dockerBuild

# Export image as a standard OCI tarball
mvn compile jib:buildTar

# Gradle equivalent commands
./gradlew jib
./gradlew jibDockerBuild
./gradlew jibBuildTar
```

---

## 3. Multi-Cloud Registry Authentication Quick Reference

### Google Cloud Artifact Registry (GAR)
```bash
# Option A: Credential helper in pom.xml (<credHelper>gcr</credHelper>)
# Option B: CLI OAuth2 token
export GCP_TOKEN=$(gcloud auth print-access-token)
mvn compile jib:build \
  -Djib.to.image=us-central1-docker.pkg.dev/PROJECT_ID/REPO/APP:TAG \
  -Djib.to.auth.username=oauth2accesstoken \
  -Djib.to.auth.password=$GCP_TOKEN
```

### AWS Elastic Container Registry (ECR)
```bash
# Option A: Credential helper in pom.xml (<credHelper>ecr-login</credHelper>)
# Option B: CLI STS temporary token
export AWS_ECR_PASSWORD=$(aws ecr get-login-password --region us-east-1)
mvn compile jib:build \
  -Djib.to.image=123456789012.dkr.ecr.us-east-1.amazonaws.com/APP:TAG \
  -Djib.to.auth.username=AWS \
  -Djib.to.auth.password=$AWS_ECR_PASSWORD
```

### Azure Container Registry (ACR)
```bash
# Option A: Credential helper in pom.xml (<credHelper>acr-env</credHelper>)
# Option B: Service Principal
mvn compile jib:build \
  -Djib.to.image=mycompanyacr.azurecr.io/APP:TAG \
  -Djib.to.auth.username=$AZURE_CLIENT_ID \
  -Djib.to.auth.password=$AZURE_CLIENT_SECRET
```

### GitHub Container Registry (`ghcr.io`)
```bash
mvn compile jib:build \
  -Djib.to.image=ghcr.io/OWNER/APP:TAG \
  -Djib.to.auth.username=$GITHUB_ACTOR \
  -Djib.to.auth.password=$GITHUB_TOKEN
```

---

## 4. Jib `pom.xml` Parametrized Template

```xml
<properties>
    <container.base-image>gcr.io/distroless/java21-debian12:nonroot</container.base-image>
    <container.registry>docker.io</container.registry>
    <container.repository>mycompany</container.repository>
    <container.tag>${project.version}</container.tag>
</properties>

<plugin>
    <groupId>com.google.cloud.tools</groupId>
    <artifactId>jib-maven-plugin</artifactId>
    <version>3.4.3</version>
    <configuration>
        <from><image>${container.base-image}</image></from>
        <to><image>${container.registry}/${container.repository}/${project.artifactId}:${container.tag}</image></to>
        <container>
            <mainClass>com.example.demo.DemoApplication</mainClass>
            <jvmFlags>
                <jvmFlag>-XX:MaxRAMPercentage=75.0</jvmFlag>
                <jvmFlag>-XX:+UseG1GC</jvmFlag>
                <jvmFlag>-XX:+ExitOnOutOfMemoryError</jvmFlag>
            </jvmFlags>
            <ports><port>8080</port></ports>
            <user>nonroot:nonroot</user>
            <creationTime>USE_CURRENT_TIMESTAMP</creationTime>
        </container>
    </configuration>
</plugin>
```

---

## 5. GraalVM Native Image Commands

```bash
# Compile native binary with native-maven-plugin
mvn -Pnative clean native:compile

# Run produced machine binary (instant boot <50ms)
./target/order-service

# Build native container via Cloud Native Buildpacks (Paketo)
mvn spring-boot:build-image -Pnative

# Hybrid: Compile GraalVM native binary and push Distroless container via Jib
mvn clean package jib:build -Pnative-jib
```

---

## 🧭 Navigation & Cheatsheet Index

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Spring Security 6, JWT & OAuth2 Cheatsheet**](spring-security-6-jwt-oauth2.md) | [**All Cheatsheets**](index.md) | *(Module 7 Testing Cheatsheet Coming Soon)* |
