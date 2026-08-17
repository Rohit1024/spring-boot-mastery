---
icon: lucide/ship
---

# 0070: Kubernetes Orchestration: Pods, Deployments & Services

Docker Compose is great for local development on a single laptop, but in enterprise cloud production, microservices run across hundreds of bare-metal or cloud VMs (nodes).

**Kubernetes (K8s)** is the industry-standard container orchestration engine. It automates container provisioning, declarative zero-downtime rolling updates, auto-scaling, self-healing restarts, and service discovery.

In this lesson, you will master writing production-grade Kubernetes manifests (`Deployment`, `Service`, `ConfigMap`, `Secret`), configuring Spring Boot Actuator Liveness and Readiness probes, and tuning resource limits.

---

## 1. Kubernetes Workload Architecture for Spring Boot

``` mermaid
flowchart TD
    subgraph IngressTier["Ingress & Networking Tier"]
        Ingress["Kubernetes Ingress Controller (api.example.com)"]
        K8sService["ClusterIP Service: 'order-service' (Virtual IP: 10.96.0.100:80)"]
        Ingress --> K8sService
    end

    subgraph ConfigTier["Configuration & Secrets"]
        K8sConfigMap["ConfigMap: order-config"]
        K8sSecret["Secret: db-credentials"]
    end

    subgraph DeploymentMesh["Deployment: order-service-deployment (Replicas: 3)"]
        
        subgraph Pod1["Pod 1 (10.244.1.42)"]
            App1["Spring Boot Container (Port 8080)"]
            Probe1["Probes: /actuator/health/liveness & readiness"]
        end

        subgraph Pod2["Pod 2 (10.244.2.18)"]
            App2["Spring Boot Container (Port 8080)"]
            Probe2["Probes: /actuator/health/liveness & readiness"]
        end

        subgraph Pod3["Pod 3 (10.244.3.91)"]
            App3["Spring Boot Container (Port 8080)"]
            Probe3["Probes: /actuator/health/liveness & readiness"]
        end

    end

    K8sConfigMap -.->|Injected as Env Vars| DeploymentMesh
    K8sSecret -.->|Injected as Env Vars| DeploymentMesh
    
    K8sService -->|Load Balances TCP traffic| Pod1
    K8sService -->|Load Balances TCP traffic| Pod2
    K8sService -->|Load Balances TCP traffic| Pod3
```

---

## 2. Production Kubernetes Deployment Manifest (`deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service-deployment
  namespace: production
  labels:
    app: order-service
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Allow 1 temporary extra pod during rollout
      maxUnavailable: 0  # Zero-downtime: Never kill old pod before new pod is ready
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
    spec:
      containers:
        - name: order-service
          image: my-registry.io/order-service:1.0.0
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8080
          
          # Resource constraints to prevent OOMKilled crashes
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1024Mi"
              cpu: "1000m"

          # Environmental configuration from ConfigMaps & Secrets
          envFrom:
            - configMapRef:
                name: order-service-config
            - secretRef:
                name: order-service-secrets

          # 🚦 Liveness Probe: Kills and restarts frozen/deadlocked containers
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3

          # 🚦 Readiness Probe: Directs traffic only when application is fully ready
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: 8080
            initialDelaySeconds: 20
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 2
```

---

## 3. Kubernetes Service Manifest (`service.yaml`)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: order-service
  namespace: production
spec:
  type: ClusterIP # Internal load-balanced Virtual IP
  selector:
    app: order-service
  ports:
    - protocol: TCP
      port: 80        # Service port
      targetPort: 8080 # Target Spring Boot container port
```

---

## 4. ConfigMap & Secret Manifests

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: order-service-config
  namespace: production
data:
  SPRING_PROFILES_ACTIVE: "prod"
  SPRING_KAFKA_BOOTSTRAP_SERVERS: "kafka-service:9092"
  SPRING_DATA_REDIS_HOST: "redis-service"
---
apiVersion: v1
kind: Secret
metadata:
  name: order-service-secrets
  namespace: production
type: Opaque
stringData:
  SPRING_DATASOURCE_USERNAME: "prod_db_user"
  SPRING_DATASOURCE_PASSWORD: "SuperEncryptedProdPassword123!"
```

---

## 5. Horizontal Pod Autoscaler (`hpa.yaml`)

Automatically scales pods between 3 and 10 based on CPU & Memory load:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: order-service-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-service-deployment
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

## 6. Spring Boot 3 vs Spring Boot 4 Evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **K8s Probes** | Actuator `/actuator/health/liveness` and `/readiness` enabled automatically inside K8s environments. | Native graceful shutdown lifecycle coordinated with Kubernetes pre-stop hooks. |
| **Config Trees** | `spring.config.import=configtree:/etc/config/` mounts K8s ConfigMaps as files. | Dynamic in-memory ConfigMap watcher updating beans without restart. |
| **GraalVM Native Image** | Starts up in < 50ms, allowing Kubernetes HPA to scale pods from 0 to 50 instantaneously. | Microsecond container cold starts with zero memory warmup penalty. |

---

## 7. Primary Sources & Further Reading

- [Kubernetes Official Documentation](https://kubernetes.io/docs/) — Pods, Deployments, Services, and HPA.
- [Spring Boot Kubernetes Reference Guide](https://docs.spring.io/spring-boot/reference/features/cloud-deployments.html#cloud-deployments.kubernetes).
- [Kubernetes Best Practices: Resource Requests and Limits](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/).

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the difference between a Liveness Probe and a Readiness Probe in Kubernetes?"
    **Answer**: A Liveness Probe detects if the container is frozen/deadlocked and restarts it, while a Readiness Probe detects if the container is ready to accept user network traffic.

??? question "Question 2: Why should `maxUnavailable: 0` be configured in a Deployment's RollingUpdate strategy?"
    **Answer**: To guarantee zero-downtime deployments by ensuring Kubernetes never terminates an existing healthy pod until a new pod has fully passed its readiness probe.

??? question "Question 3: How does a Kubernetes ClusterIP Service discover which Pods to route traffic to?"
    **Answer**: By matching the Service's `selector: app: order-service` label against the labels declared on running Pods.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0069: Dockerfile Multi-Stage Builds & Docker Compose**](0069-dockerfile-multistage-builds-docker-compose.md) | [**All Lessons**](index.md) | [➡️ **0071: Cloud CI/CD: AWS CodePipeline & Elastic Beanstalk**](0071-cloud-cicd-aws-codepipeline-beanstalk.md) |

🎉 **Lesson 0070 completed! Proceed to Lesson 0071 to master automated continuous integration and continuous deployment (CI/CD) pipelines.**
