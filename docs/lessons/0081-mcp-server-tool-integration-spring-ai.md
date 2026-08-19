---
icon: lucide/plug-zap
---

# 0081: Model Context Protocol (MCP) server and tool integration with Spring AI

Traditional LLMs are isolated within their parameter weights, they cannot query live inventory databases, cancel a customer's order, or execute internal microservice APIs directly.

Initially, developers built proprietary function-calling wrappers for each provider. **The Model Context Protocol (MCP)**, open-sourced by Anthropic and adopted across the AI industry, provides a universal, standardized open protocol connecting AI models to external tools, resources, and live data sources (the *"USB-C for AI integrations"*).

In this lesson, you will master the architecture of MCP (Hosts, Clients, Servers), building executable `@Tool` functions and `java.util.function.Function` beans in Spring AI, and exposing Spring Boot microservices as full MCP Tool Servers.

---

## 1. Model context protocol (MCP) architecture

``` mermaid
flowchart TD
    subgraph MCPClientTier["MCP Client / Host Application"]
        UserApp["Spring Boot AI Application (ChatClient)"]
        LLMEngine["LLM (Claude 3.5 Sonnet / GPT-4o / Gemini 1.5 Pro)"]
        UserApp <--> LLMEngine
    end

    subgraph MCPTransportLayer["Universal Transport Protocol (STDIO / SSE HTTP)"]
        JSONRPC["JSON-RPC 2.0 Protocol Messages"]
    end

    subgraph MCPServerTier["Spring Boot MCP Server (Microservices)"]
        MCPServer["Spring AI MCP Server Adapter"]
        
        subgraph ExposedCapabilities["Exposed Capabilities"]
            Tool1["Tool: checkOrderStatus(orderId)"]
            Tool2["Tool: processRefund(orderId, amount)"]
            Resource1["Resource: db://schema/orders"]
        end
        
        MCPServer --> Tool1
        MCPServer --> Tool2
        MCPServer --> Resource1
    end

    subgraph BackendEnterpriseSystems["Enterprise Microservices & Databases"]
        OrderDB[("PostgreSQL Database")]
        PaymentGateway["Stripe Payment Service"]
        
        Tool1 --> OrderDB
        Tool2 --> PaymentGateway
    end

    UserApp <-->|JSON-RPC over STDIO or SSE| JSONRPC
    JSONRPC <--> MCPServer
```

---

## 2. Spring AI function calling basics

Before MCP, Spring AI introduced declarative Function Calling by registering standard `java.util.function.Function` beans annotated with `@Description`:

```java
package com.example.config;

import com.fasterxml.jackson.annotation.JsonPropertyDescription;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Description;

import java.util.function.Function;

@Configuration
public class AiToolConfig {

    public record OrderStatusRequest(
            @JsonPropertyDescription("The unique alphanumeric order ID, e.g. ORD-9921") 
            String orderId
    ) {}

    public record OrderStatusResponse(String orderId, String status, String estimatedDelivery) {}

    @Bean
    @Description("Fetch the real-time shipping and fulfillment status of a customer order")
    public Function<OrderStatusRequest, OrderStatusResponse> getOrderStatusTool() {
        return request -> {
            // Business logic querying database or external microservice
            return new OrderStatusResponse(request.orderId(), "OUT_FOR_DELIVERY", "2026-08-18 14:00");
        };
    }
}
```

### Invoking tools via `ChatClient`

```java
@Service
public class CustomerSupportBotService {

    private final ChatClient chatClient;

    public CustomerSupportBotService(ChatClient.Builder builder) {
        this.chatClient = builder
                .defaultSystem("You are a customer service assistant with direct access to order fulfillment tools.")
                .build();
    }

    public String handleCustomerInquiry(String userPrompt) {
        return chatClient.prompt()
                .user(userPrompt)
                .functions("getOrderStatusTool") // Enables LLM to automatically invoke the function!
                .call()
                .content();
    }
}
```

---

## 3. Building an enterprise Spring AI MCP server

With Spring AI's native MCP integration, you can expose your entire Spring Boot microservice as an **MCP Server** accessible by any MCP client (including Claude Desktop, Cursor IDE, or other Spring Boot AI clients):

### Maven dependencies (`pomxml`)

```xml
<dependency>
    <groupId>org.springframework.ai</groupId>
    <artifactId>spring-ai-mcp-server-spring-boot-starter</artifactId>
</dependency>
```

### Exposing executable MCP tools with `@Tool`

```java
package com.example.mcp.tools;

import com.example.service.OrderManagementService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Component;

@Slf4j
@Component
@RequiredArgsConstructor
public class OrderMcpToolSet {

    private final OrderManagementService orderService;

    @Tool(name = "cancel_customer_order", description = "Cancels an in-flight order and issues a customer refund")
    public String cancelOrder(
            @ToolParam(description = "The alphanumeric order ID to cancel") String orderId,
            @ToolParam(description = "Reason provided by the customer for cancellation") String reason) {
        
        log.info("MCP Tool Invocation: Cancelling order {} for reason: {}", orderId, reason);
        boolean success = orderService.cancelAndRefund(orderId, reason);
        return success 
                ? "Order " + orderId + " has been successfully cancelled and refund initiated."
                : "Failed to cancel order " + orderId + ". It may have already shipped.";
    }

    @Tool(name = "check_inventory_stock", description = "Checks the available warehouse inventory stock for a product SKU")
    public int checkStock(@ToolParam(description = "Product SKU code") String sku) {
        return orderService.getAvailableStock(sku);
    }
}
```

---

## 4. Configuring MCP transports: Stdio vs SSE

Spring AI MCP supports two universal transport mechanisms in `application.yml`:

```yaml
spring:
  ai:
    mcp:
      server:
        name: enterprise-order-mcp-server
        version: 1.0.0
        # 1. STDIO Transport: Ideal for local CLI agents and IDE plugins (Cursor, Claude Desktop)
        type: STDIO
        
        # 2. SSE HTTP Transport: Ideal for cloud microservices communication
        # type: SSE
        # sse:
        #   port: 8090
        #   endpoint: /mcp/message
```

---

## 5. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **Tool Calling Model** | Spring AI `FunctionCallback` and MCP JSON-RPC 2.0 adapters. | First-class Java reflection-free `@Tool` method interceptors. |
| **Transport Protocols** | STDIO and HTTP SSE transports. | Bidirectional HTTP/3 WebTransport and gRPC MCP multiplexed channels. |
| **Agentic Tool Governance**| Manual permission guards and prompt engineering. | Cryptographically verified zero-trust AI tool capability tokens and RBAC checks. |

---

## 6. Primary sources and further reading

- [Model Context Protocol (MCP) Specification](https://modelcontextprotocol.io/), Anthropic's official MCP standard.
- [Spring AI MCP Reference Documentation](https://docs.spring.io/spring-ai/reference/api/mcp.html).
- [Spring AI Function Calling Guide](https://docs.spring.io/spring-ai/reference/api/chatclient.html#_function_calling).

---

## 7. Knowledge check and practice

??? question "Question 1: What is the primary purpose of the Model Context Protocol (MCP)?"
    **Answer**: To provide an open, standardized protocol connecting AI models to external tools, databases, and microservices regardless of the specific LLM vendor.

??? question "Question 2: What are the three core capability types exposed by an MCP Server?"
    **Answer**: Tools (executable functions with side effects), Resources (read-only contextual data/files), and Prompts (pre-engineered prompt templates).

??? question "Question 3: How does Spring AI connect a Java method to an LLM for automated execution?"
    **Answer**: By registering a `@Bean` `Function<Request, Response>` annotated with `@Description` or using the `@Tool` annotation, which Spring AI converts into a tool specification sent to the LLM.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0080: RAG with Vector Stores & Embeddings**](0080-rag-vector-stores-embeddings-spring-ai.md) | [**All Lessons**](index.md) | 🏆 **Curriculum Completed! Review Cheatsheets & Debugging Guides** |

---

## Course completion

You have completed all **14 Modules (81 Lessons)** spanning:
1. **Spring Core Fundamentals & IoC** (Lessons 0001-0005)
2. **RESTful Web Services & Spring MVC** (Lessons 0006-0011)
3. **Persistence Mastery: Hibernate & Spring Data JPA** (Lessons 0012-0017)
4. **Observability, Logging & OpenAPI** (Lessons 0018-0022)
5. **Spring Security 6, OAuth2 & JWT** (Lessons 0023-0027)
6. **Packaging & Containerizing: Jib & GraalVM Native** (Lessons 0028-0032)
7. **Batch Processing, Quartz & ShedLock** (Lessons 0033-0037)
8. **Alternative Protocols: GraphQL, gRPC & WebSockets** (Lessons 0038-0041)
9. **Architecture Paradigms: Modulith & Virtual Threads** (Lessons 0042-0044)
10. **Vendor-Neutral Observability: Prometheus & OTel** (Lessons 0045-0047)
11. **Enterprise Testing: JUnit 5, Mockito & Testcontainers** (Lessons 0048-0051)
12. **High-Performance Caching & Messaging: Redis & Kafka** (Lessons 0052-0056)
13. **Microservices, Kubernetes & Cloud CI/CD** (Lessons 0057-0071)
14. **Reactive Programming (WebFlux) & Spring AI** (Lessons 0072-0081)

Explore the [**Architecture & Command Cheatsheets**](../cheatsheet/index.md), review [**Diagnostic Debugging Playbooks**](../debugging/index.md), and test yourself against [**Senior / Staff Interview Questions**](../interview/index.md)!
