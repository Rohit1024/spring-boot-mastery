# Learning Record 0007: Module 6 — Packaging, Jib & GraalVM Native Completed

- **Date**: 2026-08-17
- **Module**: Module 6: Building, Packaging & Containerizing Spring Boot Applications
- **Status**: Completed

## Concepts Mastered

1. **Spring Boot Packaging Mechanics**:
   - Fat JAR internals: `JarLauncher`, nested JAR classloading, and `BOOT-INF/` structure.
   - Layered JAR extraction with `jarmode=layertools` into four cache-friendly layers (`dependencies`, `spring-boot-loader`, `snapshot-dependencies`, `application`).
   - Production multi-stage Dockerfile architecture with non-root security (`UID 10001`) and JVM container memory ergonomics (`-XX:MaxRAMPercentage=75.0`).
   - Base image selection trade-offs (Eclipse Temurin, Alpine, Google Distroless, Chainguard).

2. **Google Jib Daemonless Containerization**:
   - Building and pushing OCI/Docker container images directly from Maven/Gradle without requiring a Docker daemon, Docker CLI, or root socket permissions.
   - Automatic 4-layer construction and cryptographic hash validation for sub-2-second rebuilds on code changes.
   - Execution goals: `jib:build` (direct to registry), `jib:dockerBuild` (local Docker daemon), and `jib:buildTar` (air-gapped archive).

3. **Multi-Cloud Artifact Registry Authentication & Portability**:
   - Automated authentication with Google Cloud Artifact Registry (`docker-credential-gcr` / OAuth2 token), AWS ECR (`docker-credential-ecr-login` / STS token), Azure ACR (`docker-credential-acr-env` / Service Principal), and GitHub Container Registry (`ghcr.io`).
   - Externalizing container target URLs, base images, repository paths, and tags into Maven properties and CLI `-D` flags for environment portability.

4. **GraalVM Ahead-Of-Time (AOT) Compilation**:
   - HotSpot JIT vs GraalVM AOT: Closed-World Assumption, dead code elimination, and SubstrateVM embedding.
   - Spring Boot AOT processing engine generating static source code and reachability hints at build time.
   - Compiling native machine executables with `native-maven-plugin` achieving sub-50ms boot times and ~30MB RSS footprint.
   - Custom reachability hints via `@RegisterReflectionForBinding` and `RuntimeHintsRegistrar`.

5. **Containerizing Native Executables with Jib & Distroless**:
   - Packaging compiled GraalVM native binaries into `gcr.io/distroless/base-debian12` using Jib's `extraDirectories` and entrypoint overrides without a Docker daemon.
   - Achieving ultra-small (~45MB) production container images with 0 CVE vulnerabilities and instant cold starts.

## Artifacts Produced

- Lessons: `0028`, `0029`, `0030`, `0031`, `0032` (with Spring Boot 3 vs 4 comparisons).
- Cheatsheet: `docs/cheatsheet/spring-boot-jib-docker-native.md`.
- Debugging Guide: `docs/debugging/jib-cloud-auth-and-graalvm-native-pitfalls.md`.
- Interview Questions: 10 high-signal containerization and native image questions in `docs/interview/index.md`.
- Glossary: Added definitions for Fat JAR, Layered JAR, Jib, OCI, Distroless, GraalVM AOT, Closed-World Assumption, SubstrateVM, Reachability Metadata, and Credential Helper.
