---
icon: lucide/search
---

# 0022: Centralized Logging with ELK Stack (Elasticsearch, Logstash, Kibana) & Filebeat

In a distributed microservices ecosystem consisting of dozens of independent services across Kubernetes nodes, inspecting individual container logs via SSH or `kubectl logs` is completely unscalable. 

The **ELK Stack (Elasticsearch, Logstash, Kibana)** is the enterprise gold standard for centralizing, indexing, and visualizing millions of structured log events per second. In this lesson, you will architect an end-to-end log shipping pipeline, stream logs via TCP socket appenders, orchestrate a local ELK cluster with Docker Compose, and perform distributed request tracing using Kibana Query Language (KQL).

---

## 1. The Centralized Logging Pipeline Architecture

``` mermaid
flowchart TD
    subgraph Microservices["Microservice Fleet (Docker / K8s)"]
        S1["Order Service<br/><i>(JSON Logs)</i>"]
        S2["Payment Service<br/><i>(JSON Logs)</i>"]
        S3["Inventory Service<br/><i>(JSON Logs)</i>"]
    end

    subgraph LogShipper["Log Ingestion & Shipping"]
        Logstash["⚡ Logstash (:5000)<br/>Filters, GeoIP, Transformations"]
    end

    subgraph Storage["Distributed Search & Analytics"]
        ES["🗄️ Elasticsearch Cluster (:9200)<br/>Inverted Index & Time-Series Data"]
    end

    subgraph Visualization["UI Dashboards"]
        Kibana["🖥️ Kibana (:5601)<br/>Live Tail, Histograms, KQL Search"]
    end

    S1 -->|TCP Socket / Filebeat| Logstash
    S2 -->|TCP Socket / Filebeat| Logstash
    S3 -->|TCP Socket / Filebeat| Logstash
    
    Logstash -->|Bulk REST Indexing| ES
    Kibana -->|Query REST API| ES
```

---

## 2. Direct TCP Socket Streaming from Logback

Rather than writing to disk and relying on a separate agent, Spring Boot can stream JSON log events directly over TCP to Logstash using `LogstashTcpSocketAppender`:

### `pom.xml`
```xml
<dependency>
    <groupId>net.logstash.logback</groupId>
    <artifactId>logstash-logback-encoder</artifactId>
    <version>8.0</version>
</dependency>
```

### `logback-spring.xml` (TCP Appender)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>

    <!-- Async TCP Socket Appender to Logstash -->
    <appender name="LOGSTASH_TCP" class="net.logstash.logback.appender.LogstashTcpSocketAppender">
        <destination>${LOGSTASH_HOST:localhost}:${LOGSTASH_PORT:5000}</destination>
        
        <!-- Reconnection & Ring Buffer Queuing on Network Failure -->
        <reconnectionDelay>5 seconds</reconnectionDelay>
        <ringBufferSize>16384</ringBufferSize>
        
        <encoder class="net.logstash.logback.encoder.LogstashEncoder">
            <customFields>{"app":"spring-masterclass","service":"order-service"}</customFields>
            <includeMdcKeyName>traceId</includeMdcKeyName>
            <includeMdcKeyName>userId</includeMdcKeyName>
            <includeMdcKeyName>clientIp</includeMdcKeyName>
        </encoder>
    </appender>

    <root level="INFO">
        <appender-ref ref="LOGSTASH_TCP"/>
    </root>

</configuration>
```

---

## 3. Logstash Pipeline Configuration (`logstash.conf`)

Logstash receives TCP payloads on port `5000`, parses incoming JSON, and ships documents in bulk to Elasticsearch:

```ruby
# logstash/pipeline/logstash.conf
input {
  tcp {
    port => 5000
    codec => json_lines
  }
}

filter {
  # Add custom parsing, GeoIP resolution, or field pruning if needed
  if [level] == "ERROR" {
    mutate { add_tag => [ "alert_candidate" ] }
  }
}

output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    index => "spring-logs-%{+YYYY.MM.dd}"
  }
}
```

---

## 4. Local Observability Stack (`docker-compose.yml`)

You can spin up an entire local ELK stack alongside your Spring Boot microservice in one command:

```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.15.0
    container_name: elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    networks:
      - logging-net

  logstash:
    image: docker.elastic.co/logstash/logstash:8.15.0
    container_name: logstash
    volumes:
      - ./logstash/pipeline/logstash.conf:/usr/share/logstash/pipeline/logstash.conf:ro
    ports:
      - "5000:5000/tcp"
    environment:
      - "LS_JAVA_OPTS=-Xms256m -Xmx256m"
    depends_on:
      - elasticsearch
    networks:
      - logging-net

  kibana:
    image: docker.elastic.co/kibana/kibana:8.15.0
    container_name: kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    networks:
      - logging-net

networks:
  logging-net:
    driver: bridge
```

---

## 5. Querying Logs in Kibana with KQL

Once the stack is running, access Kibana at `http://localhost:5601` and navigate to **Discover**.

``` mermaid
sequenceDiagram
    autonumber
    actor SRE as SRE / Developer
    participant Kibana as Kibana UI (:5601)
    participant ES as Elasticsearch Engine (:9200)

    SRE->>Kibana: Enter KQL Query: `traceId: "c7b91a2e"`
    Kibana->>ES: POST /spring-logs-*/_search { query: { match: { traceId: "c7b91a2e" } } }
    ES-->>Kibana: Returns 12 Chronological Log Events across 3 Microservices
    Kibana-->>SRE: Displays Unified Request Timeline & Stack Traces
```

### High-Yield KQL (Kibana Query Language) Cheat-Sheet:

| Query Intent | KQL Syntax |
| :--- | :--- |
| **Filter by Service & Error Level** | `service: "order-service" and level: "ERROR"` |
| **Trace Single Request Across Fleet** | `traceId: "c7b91a2e-4f81-432a"` |
| **Find Specific Customer Failures** | `userId: "usr_42" and message: *PaymentFailed*` |
| **Find Slow Operations** | `responseTimeMs > 2000` |
| **Exclude Health Probes** | `not uri: "/actuator/*"` |

---

## 6. Primary Sources & Further Reading

- [Elasticsearch Reference Guide](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html) — Indices, mappings, and inverted index search architecture.
- [Logstash TCP Socket Documentation](https://www.elastic.co/guide/en/logstash/current/plugins-inputs-tcp.html) — Ingesting network socket telemetry.
- [Kibana Query Language (KQL) Guide](https://www.elastic.co/guide/en/kibana/current/kuery-query.html) — Mastering syntax for filtering and aggregation.

---

## 7. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the main advantage of shipping structured JSON logs directly to Logstash via TCP compared to tailing text files?"
    **Answer**: Direct TCP streaming avoids file I/O latency, eliminates custom regex parsing steps in Logstash, and enables pre-indexed JSON field ingestion directly into Elasticsearch.

??? question "Question 2: How does a shared `traceId` in MDC facilitate debugging in a distributed microservices ELK dashboard?"
    **Answer**: By searching for the single `traceId` in Kibana, engineers see the entire chronological journey of a request across all participating microservices in a single unified view.

??? question "Question 3: What does the `reconnectionDelay` and `ringBufferSize` setting in `LogstashTcpSocketAppender` provide?"
    **Answer**: It creates a non-blocking in-memory circular buffer that queues log events during temporary Logstash network outages and automatically reconnects without dropping logs or stalling worker threads.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0021: Structured Logging & MDC**](0021-structured-logging-logback-mdc.md) | [**All Lessons**](index.md) | [➡️ **0023: Spring Security 6 Architecture**](../lessons/index.md) |

🎉 **Congratulations on completing Module 4: Observability, Tooling & API Docs!**
