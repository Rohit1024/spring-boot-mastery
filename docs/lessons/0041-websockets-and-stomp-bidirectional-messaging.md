---
icon: lucide/radio
---

# 0041: Real-time messaging with WebSockets and STOMP

While Server-Sent Events (SSE) provide a lightweight mechanism for **one-way server-to-client** streaming, interactive applications, such as live trading desks, collaborative document editors, multi-player gaming, and live support chat, demand **full-duplex, bidirectional communication** with sub-millisecond latency.

Raw WebSockets establish a bidirectional TCP connection but lack higher-level application semantics (like message headers, subscriptions, or destination routing). Spring solves this by layering **STOMP (Simple Text Oriented Messaging Protocol)** on top of WebSockets.

In this lesson, you will master configuring Spring's WebSocket message broker, handling client messages with `@MessageMapping`, targeting private users with `SimpMessagingTemplate`, and scaling beyond a single server using external **STOMP Broker Relays**.

---

## 1. Protocol comparison: Polling vs SSE vs WebSockets

``` mermaid
flowchart TD
    subgraph Polling["1. Short or Long Polling"]
        CP["Client"] -->|Frequent HTTP GET Requests| SP["Server"]
        SP -->|200 OK or 304 Not Modified| CP
        CP -->|Repeats every 2 seconds| SP
    end

    subgraph SSE["2. Server-Sent Events"]
        CS["Client"] -->|GET /stream with Accept: text/event-stream| SS["Server"]
        SS -->|data: Event 1 - Server push only| CS
        SS -->|data: Event 2 - Server push only| CS
    end

    subgraph WebSockets["3. WebSockets & STOMP"]
        CW["Client"] ---|Single persistent full-duplex TCP socket| SW["Server"]
        CW -->|STOMP SEND /app/chat.send| SW
        SW -->|STOMP MESSAGE /topic/chat| CW
    end

    Polling ~~~ SSE ~~~ WebSockets
```

---

## 2. Configuring the WebSocket message broker

Enable WebSocket broker capabilities and register STOMP endpoints:

### `WebSocketConfig.java`
```java
package com.example.websocket.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // 1. Register the WebSocket handshake endpoint
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*")
                .withSockJS(); // Fallback for browsers lacking native WebSocket support
    }

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        // 2. Client send prefix for messages routed to @MessageMapping controllers
        registry.setApplicationDestinationPrefixes("/app");

        // 3. Built-in In-Memory broker for broadcasting to subscribed clients
        registry.enableSimpleBroker("/topic", "/queue");

        // 4. Prefix for targeting individual private user queues
        registry.setUserDestinationPrefix("/user");
    }
}
```

---

## 3. Handling messages: `@MessageMapping` `@SendTo`

When clients send messages to `/app/chat.sendMessage`, the controller method intercepts, enriches, and broadcasts the payload to all clients subscribed to `/topic/public`:

```java
package com.example.websocket.controller;

import com.example.websocket.dto.ChatMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.messaging.simp.SimpMessageHeaderAccessor;
import org.springframework.stereotype.Controller;

import java.time.Instant;

@Controller
public class ChatController {

    private static final Logger log = LoggerFactory.getLogger(ChatController.class);

    // Maps to: SEND destination '/app/chat.sendMessage'
    @MessageMapping("/chat.sendMessage")
    // Broadcasts output to all subscribers on '/topic/public'
    @SendTo("/topic/public")
    public ChatMessage sendMessage(@Payload ChatMessage message) {
        log.info("Broadcasting chat message from: {}", message.sender());
        return new ChatMessage(
                message.sender(),
                message.content(),
                Instant.now().toString()
        );
    }

    // Handles user join event and binds username to WebSocket session attributes
    @MessageMapping("/chat.addUser")
    @SendTo("/topic/public")
    public ChatMessage addUser(@Payload ChatMessage message, SimpMessageHeaderAccessor headerAccessor) {
        headerAccessor.getSessionAttributes().put("username", message.sender());
        log.info("User joined: {}", message.sender());
        return new ChatMessage(
                "SYSTEM",
                message.sender() + " joined the room!",
                Instant.now().toString()
        );
    }
}
```

---

## 4. Sending private targeted messages (`simpmessagingtemplate`)

To send private notifications or alerts directly to a single authenticated user (e.g. `user123`):

```java
package com.example.websocket.service;

import com.example.websocket.dto.PrivateNotification;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

@Service
public class UserNotificationService {

    private final SimpMessagingTemplate messagingTemplate;

    public UserNotificationService(SimpMessagingTemplate messagingTemplate) {
        this.messagingTemplate = messagingTemplate;
    }

    public void sendPrivateAlert(String username, String alertMessage) {
        PrivateNotification notification = new PrivateNotification("SECURITY_ALERT", alertMessage);
        
        // Pushes to destination: '/user/{username}/queue/notifications'
        messagingTemplate.convertAndSendToUser(
                username, 
                "/queue/notifications", 
                notification
        );
    }
}
```
*(The target client subscribes to `/user/queue/notifications` on the frontend).*

---

## 5. Scaling across multiple servers: External STOMP broker relay

In production with multiple clustered Spring Boot pods, the in-memory simple broker **cannot route messages to clients connected to different pods**.

To scale horizontally, replace the in-memory broker with a **STOMP Broker Relay** connected to an external message broker (RabbitMQ or ActiveMQ):

``` mermaid
flowchart TD
    subgraph ClientFleet["Connected Clients"]
        Client1["Client 1 (Pod A)"]
        Client2["Client 2 (Pod B)"]
    end

    subgraph SpringPods["Spring Boot Cluster"]
        PodA["Pod A (Spring WebSocket)"]
        PodB["Pod B (Spring WebSocket)"]
    end

    subgraph ExternalBroker["Dedicated Message Broker (RabbitMQ / ActiveMQ)"]
        RabbitSTOMP["RabbitMQ STOMP Plugin (:61613)<br/><i>(Synchronizes topics across all server nodes)</i>"]
    end

    Client1 <==>|WebSocket| PodA
    Client2 <==>|WebSocket| PodB
    
    PodA <==>|TCP STOMP Relay| RabbitSTOMP
    PodB <==>|TCP STOMP Relay| RabbitSTOMP
```

### Configuring rabbitmq STOMP relay
```java
@Override
public void configureMessageBroker(MessageBrokerRegistry registry) {
    registry.setApplicationDestinationPrefixes("/app");
    
    // Connects to external RabbitMQ STOMP adapter instead of in-memory broker
    registry.enableStompBrokerRelay("/topic", "/queue")
            .setRelayHost("rabbitmq.production.internal")
            .setRelayPort(61613)
            .setClientLogin("guest")
            .setClientPasscode("guest")
            .setSystemLogin("guest")
            .setSystemPasscode("guest");
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4: WebSocket evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x"]
        NettyTomcatWs["Tomcat / Undertow WebSocket Engine"]
        ThreadBoundSessions["ThreadLocal WebSocket Session Adapters"]
        SockJsFallback["Standard SockJS Polyfill Protocols"]
    end

    subgraph SB4["Spring Boot 4.x"]
        LoomWebSockets["Virtual-Thread Native Concurrent WebSockets"]
        NativeWebTransport["HTTP/3 WebTransport Direct Streams"]
        AOTMessageMapping["AOT Compiled STOMP Payload Converters"]
    end

    SB3 ==>|Massive Concurrency & HTTP/3 Transport| SB4
```

### Key differences and configuration comparison

| WebSocket Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Concurrent Connection Scaling** | Bound by platform thread pools during message dispatch. | **Loom Virtual Threads**: Millions of concurrent open WebSocket connections with minimal RAM. |
| **Transport Modernization** | Standard WebSocket (TCP) with SockJS HTTP fallback. | **HTTP/3 WebTransport Integration**: UDP-based multiplexed transport eliminating head-of-line blocking. |
| **Serialization Performance** | Jackson reflection on `@Payload` types. | **AOT Pre-Generated Binary Codecs**: Instant binary and JSON STOMP message parsing. |

---

## 7. Primary sources and further reading

- [Spring Framework Reference: WebSocket & STOMP Messaging](https://docs.spring.io/spring-framework/reference/web/websocket.html), Comprehensive architecture and configuration guide.
- [STOMP Protocol Specification v1.2](https://stomp.github.io/stomp-specification-1.2.html), Frame structures, commands, and headers.
- [RabbitMQ STOMP Plugin Guide](https://www.rabbitmq.com/docs/stomp), Setting up clustered external broker relays.

---

## 8. Knowledge check and practice

??? question "Question 1: Why is STOMP preferred over raw WebSockets in enterprise Spring Boot applications?"
    **Answer**: Raw WebSockets only provide a raw byte/text stream; STOMP adds a standardized messaging protocol with headers, destination routing (`/topic`, `/queue`), and subscription semantics.

??? question "Question 2: What is the purpose of `SimpMessagingTemplate.convertAndSendToUser()`?"
    **Answer**: It routes a targeted private message to a specific authenticated user's private queue (e.g. `/user/{username}/queue/notifications`) rather than broadcasting to all connected clients.

??? question "Question 3: Why is an external STOMP Broker Relay (like RabbitMQ) mandatory when scaling Spring Boot WebSocket services across multiple Kubernetes pods?"
    **Answer**: The in-memory simple broker only routes messages to clients connected to that specific local JVM instance; an external broker relay synchronizes topics across all cluster pods.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0040: Spring gRPC & Protocol Buffers**](0040-spring-grpc-and-protocol-buffers-microservices.md) | [**All Lessons**](index.md) | [ **0042: Spring Modulith Modular Monoliths**](0042-spring-modulith-modular-monoliths-ddd.md) |

🎉 **Congratulations on completing Module 8: Alternative API Protocols (GraphQL, gRPC & WebSockets)!**
