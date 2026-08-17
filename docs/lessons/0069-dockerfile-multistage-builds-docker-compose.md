---
icon: lucide/container
---

# 0069: Containerization: Dockerfile Multi-Stage Builds & Docker Compose

Deploying fat JARs directly onto cloud virtual machines creates environment inconsistencies ("works on my machine") and complicates dependency updates.

In enterprise production, applications are packaged as lightweight, immutable **OCI/Docker container images**. Naive Dockerfiles bundle full Maven JDKs and source files into the runtime image, resulting in bloated 800MB+ images with severe security vulnerabilities.

In this lesson, you will master writing secure 3-stage multi-stage Dockerfiles leveraging Spring Boot Layered JARs, running containers as non-root users, and orchestrating full microservice stacks (PostgreSQL, Kafka, Redis, Zipkin) using Docker Compose.

---

## 1. Multi-Stage Build & Layered JAR Pipeline

``` mermaid
flowchart TD
    subgraph Stage1["Stage 1: Maven Builder (eclipse-temurin:21-jdk)"]
        SourceCode["Java Source + pom.xml"]
        MvnBuild["mvn clean package -DskipTests"]
        FatJar["app.jar (Fat Executable JAR)"]
        SourceCode --> MvnBuild --> FatJar
    end

    subgraph Stage2["Stage 2: Layer Extractor (eclipse-temurin:21-jre)"]
        ExtractLayers["java -Djarmode=layertools -jar app.jar extract"]
        LayerDep["dependencies/"]
        LayerSnap["snapshot-dependencies/"]
        LayerSpring["spring-boot-loader/"]
        LayerApp["application/"]
        
        FatJar --> ExtractLayers
        ExtractLayers --> LayerDep
        ExtractLayers --> LayerSnap
        ExtractLayers --> LayerSpring
        ExtractLayers --> LayerApp
    end

    subgraph Stage3["Stage 3: Distroless / Alpine JRE Runtime (eclipse-temurin:21-jre-alpine)"]
        NonRootUser["Security: Run as non-root user (appuser:10001)"]
        Assemble["COPY cached layers in order of change frequency"]
        RunCmd["ENTRYPOINT java org.springframework.boot.loader.launch.JarLauncher"]
        
        LayerDep --> Assemble
        LayerSnap --> Assemble
        LayerSpring --> Assemble
        LayerApp --> Assemble
        Assemble --> NonRootUser --> RunCmd
    end

    Stage1 --> Stage2 --> Stage3
```

---

## 2. Production Hardened Multi-Stage `Dockerfile`

```dockerfile
# ==========================================
# STAGE 1: Dependency & Compilation Builder
# ==========================================
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /build

# Cache Maven dependencies layer
COPY pom.xml .
COPY .mvn .mvn
COPY mvnw .
RUN chmod +x ./mvnw && ./mvnw dependency:go-offline -B

# Compile application
COPY src src
RUN ./mvnw clean package -DskipTests -B

# ==========================================
# STAGE 2: Layered JAR Extraction
# ==========================================
FROM eclipse-temurin:21-jre-alpine AS extractor
WORKDIR /extracted
COPY --from=builder /build/target/*.jar app.jar
RUN java -Djarmode=layertools -jar app.jar extract

# ==========================================
# STAGE 3: Hardened Runtime Image
# ==========================================
FROM eclipse-temurin:21-jre-alpine AS runtime
WORKDIR /app

# 🔒 Security: Create non-root system group and user
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Copy layers in order of lowest to highest modification frequency
COPY --from=extractor --chown=appuser:appgroup /extracted/dependencies/ ./
COPY --from=extractor --chown=appuser:appgroup /extracted/spring-boot-loader/ ./
COPY --from=extractor --chown=appuser:appgroup /extracted/snapshot-dependencies/ ./
COPY --from=extractor --chown=appuser:appgroup /extracted/application/ ./

USER appuser:appgroup
EXPOSE 8080

# Configure JVM memory limits for container environments
ENV JAVA_OPTS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0 -XX:+UseG1GC"

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS org.springframework.boot.loader.launch.JarLauncher"]
```

---

## 3. Local Microservices Stack with `docker-compose.yml`

This unified Docker Compose environment orchestrates PostgreSQL, Redis, Apache Kafka (KRaft mode), Zipkin, and your Spring Boot application:

```yaml
version: '3.8'

services:
  # 1. PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: postgres-db
    environment:
      POSTGRES_DB: microservices_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secretpassword
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - microservice-net

  # 2. Redis In-Memory Cache & Rate Limiter
  redis:
    image: redis:7.2-alpine
    container_name: redis-cache
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    networks:
      - microservice-net

  # 3. Apache Kafka (KRaft Mode - No ZooKeeper needed)
  kafka:
    image: confluentinc/cp-kafka:7.6.0
    container_name: kafka-broker
    ports:
      - "9092:9092"
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: 'CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT'
      KAFKA_ADVERTISED_LISTENERS: 'PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092'
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
      KAFKA_PROCESS_ROLES: 'broker,controller'
      KAFKA_CONTROLLER_QUORUM_VOTERS: '1@kafka:29093'
      KAFKA_LISTENERS: 'PLAINTEXT://0.0.0.0:29092,CONTROLLER://0.0.0.0:29093,PLAINTEXT_HOST://0.0.0.0:9092'
      KAFKA_INTER_BROKER_LISTENER_NAME: 'PLAINTEXT'
      KAFKA_CONTROLLER_LISTENER_NAMES: 'CONTROLLER'
      KAFKA_LOG_DIRS: '/tmp/kraft-combined-logs'
      CLUSTER_ID: 'MkU3OEVBNTcwNTJENDM2Qk'
    networks:
      - microservice-net

  # 4. Distributed Tracing with Zipkin
  zipkin:
    image: openzipkin/zipkin:latest
    container_name: zipkin-tracing
    ports:
      - "9411:9411"
    networks:
      - microservice-net

  # 5. Spring Boot Order Service
  order-service:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: order-service-app
    ports:
      - "8080:8080"
    environment:
      SPRING_DATASOURCE_URL: jdbc:postgresql://postgres:5432/microservices_db
      SPRING_DATASOURCE_USERNAME: postgres
      SPRING_DATASOURCE_PASSWORD: secretpassword
      SPRING_DATA_REDIS_HOST: redis
      SPRING_KAFKA_BOOTSTRAP_SERVERS: kafka:29092
      MANAGEMENT_ZIPKIN_TRACING_ENDPOINT: http://zipkin:9411/api/v2/spans
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - microservice-net

volumes:
  postgres_data:

networks:
  microservice-net:
    driver: bridge
```

---

## 4. Launching the Local Stack

```bash
# Build images and start all services in detached background mode
docker compose up --build -d

# Verify all containers are healthy
docker compose ps

# View live correlated logs
docker compose logs -f order-service
```

---

## 5. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Layer Extraction Launcher** | `org.springframework.boot.loader.launch.JarLauncher` (Spring Boot 3.2+). | Native OCI image manifest slicing with zero-JVM container launchers. |
| **Local Dev Composition** | `spring-boot-docker-compose` auto-starts containers on `mvn spring-boot:run`. | Unified cloud-native DevServices integration across Docker and Podman. |
| **Base Image Size** | Alpine / Distroless JRE images (~160MB). | Minimal GraalVM native distroless scratch images (< 35MB). |

---

## 6. Primary Sources & Further Reading

- [Spring Boot Layered JAR Docker Packaging Guide](https://docs.spring.io/spring-boot/reference/packaging/container-images/dockerfiles.html).
- [Docker Compose Specification](https://docs.docker.com/compose/compose-file/).
- [Eclipse Temurin Official Container Images](https://hub.docker.com/_/eclipse-temurin).

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: Why does extracting Spring Boot Layered JARs speed up Docker build and deployment times?"
    **Answer**: It isolates infrequently changing dependencies (90% of image size) into lower cached Docker layers, so only the small application layer (2MB) is rebuilt when code changes.

??? question "Question 2: Why must production containers run as a non-root user?"
    **Answer**: Running as non-root prevents container breakout attacks from gaining root-level access to the underlying host kernel and filesystem.

??? question "Question 3: What is the purpose of `depends_on: service_healthy` in Docker Compose?"
    **Answer**: It delays starting dependent application containers until collaborator services (like PostgreSQL or Redis) pass their health checks and are fully ready.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0068: CAP Theorem in Action: Consistency vs Availability**](0068-cap-theorem-consistency-availability-payments.md) | [**All Lessons**](index.md) | [➡️ **0070: Kubernetes Orchestration: Pods, Deployments & Services**](0070-kubernetes-orchestration-pods-services.md) |

🎉 **Lesson 0069 completed! Proceed to Lesson 0070 to master container orchestration in production Kubernetes clusters.**
