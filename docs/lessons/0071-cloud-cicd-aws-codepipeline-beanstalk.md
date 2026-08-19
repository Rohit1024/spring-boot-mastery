---
icon: lucide/cloud
---

# 0071: Cloud CI/CD: AWS CodePipeline, Buildspec, and Elastic Beanstalk

Manual server deployments via SSH and FTP are dangerous, unrepeatable, and prone to human error. In high-performing engineering organizations, every code commit pushed to a repository triggers an automated **Continuous Integration and Continuous Deployment (CI/CD)** pipeline.

An automated pipeline tests code, runs security linters, compiles container images, and executes zero-downtime rolling deployments to cloud environments like **AWS Elastic Beanstalk**, **Amazon ECS**, or **Amazon EKS**.

In this lesson, you will master configuring multi-stage CI/CD pipelines, authoring AWS `buildspec.yml` manifests, automating container pushes to Amazon Elastic Container Registry (ECR), and executing rolling cloud deployments.

---

## 1. Cloud CI/CD pipeline architecture

``` mermaid
flowchart TD
    subgraph DeveloperWorkstation["Developer Workflow"]
        DevGit["Git Commit & Push (origin main)"]
    end

    subgraph AWSCodePipeline["AWS CodePipeline Automation"]
        
        subgraph StageSource["Stage 1: Source Hook"]
            GitHubHook["GitHub / CodeCommit Webhook Trigger"]
        end
        
        subgraph StageBuild["Stage 2: AWS CodeBuild (buildspec.yml)"]
            MvnTest["1. Maven clean verify & Unit Tests"]
            SecScan["2. Dependency Vulnerability & Sonar Scan"]
            DockerBuild["3. Build & Layer Container Image"]
        end
        
        subgraph StageRegistry["Stage 3: Artifact Publishing"]
            ECRPush["Push Image to Amazon ECR (tag: git-sha)"]
        end
        
        subgraph StageDeploy["Stage 4: Automated Cloud Deployment"]
            DeployBeanstalk["AWS Elastic Beanstalk / ECS Rolling Deployment"]
            HealthCheck["Actuator /actuator/health Smoke Test"]
        end
        
    end

    subgraph CloudRuntime["AWS Cloud Production Environment"]
        ALB["Application Load Balancer (ALB)"]
        EC2Instances["Auto Scaling Group: EC2 / Fargate Instances"]
        ALB --> EC2Instances
    end

    DevGit --> GitHubHook
    GitHubHook --> StageBuild
    StageBuild --> ECRPush
    ECRPush --> DeployBeanstalk
    DeployBeanstalk --> HealthCheck
    HealthCheck --> CloudRuntime
```

---

## 2. Production AWS codebuild manifest (`buildspecyml`)

The `buildspec.yml` file defines the commands and environment settings executed by AWS CodeBuild during the pipeline run:

```yaml
version: 0.2

env:
  variables:
    JAVA_HOME: "/usr/lib/jvm/java-21-amazon-corretto"
    AWS_DEFAULT_REGION: "us-east-1"
  parameter-store:
    DOCKER_REGISTRY_URI: "/production/ecr/order-service-uri"

phases:
  install:
    runtime-versions:
      java: corretto21
    commands:
      - echo "Installing Maven dependencies..."
      - java -version
      - mvn -version

  pre_build:
    commands:
      - echo "Running unit and integration tests..."
      - mvn clean test -B
      - echo "Logging in to Amazon ECR..."
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $DOCKER_REGISTRY_URI
      - COMMIT_HASH=$(echo $CODEBUILD_RESOLVED_SOURCE_VERSION | cut -c 1-7)
      - IMAGE_TAG=${COMMIT_HASH:-latest}

  build:
    commands:
      - echo "Building and packaging Spring Boot layered Docker image..."
      - docker build -t $DOCKER_REGISTRY_URI:latest .
      - docker tag $DOCKER_REGISTRY_URI:latest $DOCKER_REGISTRY_URI:$IMAGE_TAG

  post_build:
    commands:
      - echo "Pushing image to Amazon ECR..."
      - docker push $DOCKER_REGISTRY_URI:latest
      - docker push $DOCKER_REGISTRY_URI:$IMAGE_TAG
      - echo "Writing image definitions artifact for deployment..."
      - printf '[{"name":"order-service","imageUri":"%s"}]' "$DOCKER_REGISTRY_URI:$IMAGE_TAG" > imagedefinitions.json

artifacts:
  files:
    - imagedefinitions.json
    - Dockerrun.aws.json
    - target/*.jar
```

---

## 3. AWS elastic Beanstalk container configuration (`dockerrunawsjson`)

For deploying containerized Spring Boot applications to AWS Elastic Beanstalk:

```json
{
  "AWSEBDockerrunVersion": "1",
  "Image": {
    "Name": "<ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/order-service:latest",
    "Update": "true"
  },
  "Ports": [
    {
      "ContainerPort": "8080"
    }
  ],
  "Logging": "/var/log/app"
}
```

---

## 4. Zero-downtime deployment strategies

When deploying updates to production, choose the right traffic shifting strategy:

| Deployment Strategy | Mechanism | Downtime | Rollback Speed | Resource Cost |
| :--- | :--- | :--- | :--- | :--- |
| **All-at-Once** | Updates all instances simultaneously. | 🔴 30-60s downtime during restart. | Slow | Low (No extra servers). |
| **Rolling** | Updates instances in small batches (e.g. 2 at a time). | 🟢 Zero downtime, but temporary reduced capacity. | Moderate | Low (Uses existing instances). |
| **Rolling with Additional Batch** | Spins up a new batch of servers first before updating existing instances. | 🟢 Zero downtime, 100% capacity preserved throughout. | Fast | Moderate (Temporary extra servers). |
| **Blue/Green** | Spins up a duplicate production environment (Green), tests it, and swaps DNS/Load Balancer. | 🟢 Zero downtime, lowest risk. | Instant (< 1s swap back) | High (2x infrastructure cost during rollout). |

---

## 5. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Buildpacks CI/CD** | `mvn spring-boot:build-image` creates standardized OCI images without local Dockerfile. | Native multi-architecture (ARM64 / x86_64) concurrent cross-compilation. |
| **Cloud Health Check** | Actuator `/actuator/health` directly integration with AWS ALB target group health checks. | Automated canary traffic analysis based on OpenTelemetry error rates. |
| **CD Automation** | GitOps tools (ArgoCD / Flux) syncing Git states to Kubernetes. | Direct declarative infrastructure-as-code (IaC) verification and drift repair. |

---

## 6. Primary sources and further reading

- [AWS CodePipeline User Guide](https://docs.aws.amazon.com/codepipeline/latest/userguide/welcome.html).
- [AWS CodeBuild buildspec.yml Reference](https://docs.aws.amazon.com/codebuild/latest/userguide/build-spec-ref.html).
- [Continuous Delivery: Reliable Software Releases, Jez Humble & David Farley](https://continuousdelivery.com/).

---

## 7. Knowledge check and practice

??? question "Question 1: What is the primary benefit of a Continuous Deployment (CD) pipeline?"
    **Answer**: It eliminates error-prone manual deployments by automatically building, testing, and safely deploying validated code changes to production environments.

??? question "Question 2: Why is the 'Rolling with Additional Batch' deployment strategy preferred over standard 'Rolling'?"
    **Answer**: It provisions extra instances first to maintain 100% processing capacity during the deployment, ensuring traffic spikes are handled without degradation.

??? question "Question 3: How does AWS CodeBuild use `imagedefinitions.json` in deployment stages?"
    **Answer**: It tells the downstream deployment engine (like Amazon ECS or Elastic Beanstalk) the exact container name and newly pushed ECR image tag to deploy.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0070: Kubernetes Orchestration: Pods & Deployments**](0070-kubernetes-orchestration-pods-services.md) | [**All Lessons**](index.md) | [ **0072: Blocking vs Non-Blocking I/O: The Reactive Paradigm**](0072-blocking-vs-nonblocking-reactive-paradigm.md) |

🎉 **Congratulations on completing Module 13: Microservices, Cloud & Distributed Patterns!**
