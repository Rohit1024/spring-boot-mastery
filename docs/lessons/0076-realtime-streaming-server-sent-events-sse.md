---
icon: lucide/radio
---

# 0076: Real-time streaming with Server-Sent Events (SSE)

Traditional HTTP request-response cycles require clients to constantly poll servers for updates. While WebSockets provide full-duplex communication, they require custom protocol handshakes and custom reconnection handling.

**Server-Sent Events (SSE)** is an HTTP/1.1 and HTTP/2 standard (`text/event-stream`) for **unidirectional, server-to-client real-time streaming**. SSE operates over standard HTTP, works seamlessly through corporate firewalls and proxies, and includes native automatic browser reconnection via the HTML5 `EventSource` API.

In this lesson, you will master streaming `Flux<ServerSentEvent<T>>` in Spring WebFlux, crafting custom event names and retry intervals, keeping connections alive through heartbeats, and consuming streams in JavaScript.

---

## 1. Server-sent events (SSE) streaming pipeline

``` mermaid
flowchart TD
    subgraph ClientBrowser["Web Browser / Client (HTML5 EventSource)"]
        Browser["new EventSource('/api/v1/orders/ORD-101/stream')"]
        UIUpdate["Real-Time UI Update (No Polling)"]
    end

    subgraph WebFluxServer["Spring WebFlux Server (Netty Event Loop)"]
        SSEController["OrderStreamingController"]
        SSEFlux["Flux ServerSentEvent OrderEvent"]
        KeepAliveFlux["Flux.interval(15s) Heartbeat Generator"]
    end

    subgraph EventStreamSource["Asynchronous Event Source"]
        KafkaStream["Kafka Reactive Consumer / PostgreSQL CDC"]
    end

    Browser -->|1. Initial HTTP GET with Accept: text/event-stream| SSEController
    KafkaStream --> SSEFlux
    KeepAliveFlux --> SSEFlux
    SSEFlux --> SSEController
    
    SSEController -->|2. HTTP 200 OK: Persistent Open Connection| Browser
    SSEController -.->|3. Frame: event: status-change, data: PREPARING| Browser
    SSEController -.->|4. Frame: event: status-change, data: OUT_FOR_DELIVERY| Browser
    SSEController -.->|5. Frame: event: ping, comment: keep-alive| Browser
    Browser --> UIUpdate
```

---

## 2. Real-time communication protocols compared

| Feature | Server-Sent Events (SSE) | WebSockets | HTTP Short/Long Polling |
| :--- | :--- | :--- | :--- |
| **Directionality** | Unidirectional (Server to Client only). | Bidirectional (Full Duplex). | Unidirectional (Client pulls). |
| **Protocol** | Standard HTTP/1.1 or HTTP/2. | Upgraded TCP protocol (`ws://` / `wss://`). | Standard HTTP (`POST`/`GET`). |
| **Reconnection** | Native browser auto-reconnect with `Last-Event-ID`. | Manual client-side reconnection code required. | Repetitive full HTTP round-trips. |
| **Firewall & Proxy** | 100% transparent through HTTP firewalls. | Requires proxy WebSocket upgrade support. | Fully transparent. |
| **Best Used For** | AI LLM token streaming, order tracking, notifications. | Multiplayer games, collaborative whiteboards, chat. | Infrequently updated legacy systems. |

---

## 3. Spring WebFlux SSE controller implementation

```java
package com.example.controller;

import com.example.dto.StockPriceEvent;
import com.example.service.StockPriceService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;

import java.time.Duration;
import java.time.Instant;
import java.util.UUID;

@Slf4j
@RestController
@RequestMapping("/api/v1/stocks")
@RequiredArgsConstructor
public class StockStreamingController {

    private final StockPriceService stockPriceService;

    /**
     * Streams real-time stock price changes as Server-Sent Events
     */
    @GetMapping(value = "/{symbol}/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<StockPriceEvent>> streamStockPrices(@PathVariable String symbol) {
        log.info("Client subscribed to SSE stock stream for: {}", symbol);

        // 1. Core data stream from reactive service / Kafka
        Flux<ServerSentEvent<StockPriceEvent>> dataFlux = stockPriceService.getPriceStream(symbol)
                .map(event -> ServerSentEvent.<StockPriceEvent>builder()
                        .id(UUID.randomUUID().toString())     // Unique event ID for replay
                        .event("stock-update")                // Custom event name
                        .retry(Duration.ofSeconds(3))         // Instruct browser to reconnect after 3s on drop
                        .data(event)                          // The actual payload
                        .build());

        // 2. Keep-Alive Heartbeat Stream (prevents load balancers from closing idle connections)
        Flux<ServerSentEvent<StockPriceEvent>> heartbeatFlux = Flux.interval(Duration.ofSeconds(15))
                .map(seq -> ServerSentEvent.<StockPriceEvent>builder()
                        .comment("keep-alive-ping-" + seq)
                        .build());

        // 3. Merge data events with periodic heartbeats
        return Flux.merge(dataFlux, heartbeatFlux)
                .doOnCancel(() -> log.info("Client disconnected from stock stream: {}", symbol));
    }
}
```

---

## 4. Raw wire protocol format

The HTTP wire format produced by WebFlux adheres to the W3C EventSource standard:

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream;charset=UTF-8
Transfer-Encoding: chunked

id: 8f9b-1234
event: stock-update
retry: 3000
data: {"symbol":"AAPL","price":189.45,"timestamp":"2026-08-17T14:30:00Z"}

: keep-alive-ping-1

id: 9a2c-5678
event: stock-update
retry: 3000
data: {"symbol":"AAPL","price":189.62,"timestamp":"2026-08-17T14:30:05Z"}
```

---

## 5. Client consumption with html5 javascript

```javascript
// Connect to the WebFlux SSE endpoint
const eventSource = new EventSource('/api/v1/stocks/AAPL/stream');

// Listen for named 'stock-update' events
eventSource.addEventListener('stock-update', (event) => {
    const stock = JSON.parse(event.data);
    console.log(`Live Update: ${stock.symbol} is now $${stock.price}`);
    document.getElementById('price-display').innerText = `$${stock.price}`;
});

// Handle connection errors (Browser auto-reconnects automatically!)
eventSource.onerror = (err) => {
    console.warn('SSE stream temporarily interrupted. Reconnecting...', err);
};
```

---

## 6. Spring Boot 3 vs Spring Boot 4 evolution

| Feature | Spring Boot 3.x (Spring Framework 6.x) | Spring Boot 4.x (Next-Gen Roadmap) |
| :--- | :--- | :--- |
| **HTTP Transport** | HTTP/1.1 chunked and HTTP/2 multiplexed streams. | Native HTTP/3 WebTransport and bidirectional SSE streams. |
| **LLM Streaming** | Custom `Flux<ServerSentEvent<ChatResponse>>` in Spring AI. | Native reactive SSE streaming pipeline built into `ChatClient.stream()`. |
| **Connection Multiplexing**| 1 OS connection per SSE stream on HTTP/1.1. | Zero connection limit bottlenecks using HTTP/2 multiplexed single TCP socket. |

---

## 7. Primary sources and further reading

- [W3C Server-Sent Events Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html).
- [Spring WebFlux Server-Sent Events Documentation](https://docs.spring.io/spring-framework/reference/web/webflux/controller.html#webflux-mvc-sse).
- [MDN Web Docs: Using Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events).

---

## 8. Knowledge check and practice

??? question "Question 1: What is the primary advantage of Server-Sent Events over WebSockets for one-way notifications?"
    **Answer**: SSE runs over standard HTTP without custom protocol upgrades, traverses firewalls natively, and includes built-in browser automatic reconnection.

??? question "Question 2: Why are periodic heartbeat comments (`: keep-alive`) necessary in SSE streams?"
    **Answer**: To prevent intermediate proxies, firewalls, and cloud load balancers from closing idle TCP connections due to inactivity timeouts.

??? question "Question 3: How does the `Last-Event-ID` header assist during SSE stream reconnections?"
    **Answer**: When a disconnected browser reconnects, it sends the `Last-Event-ID` header so the server can resume streaming events from that specific point in time.

---

## Navigation and next steps

| Previous | Catalog | Next |
| :--- | :---: | ---: |
| [**0075: Non-Blocking Persistence with R2DBC & Reactive Redis**](0075-nonblocking-persistence-r2dbc-reactive-redis.md) | [**All Lessons**](index.md) | [ **0077: Reactive Backpressure: Bounded flatMap & Buffers**](0077-reactive-backpressure-flatmap-buffer-strategies.md) |

🎉 **Lesson 0076 completed! Proceed to Lesson 0077 to master reactive backpressure, bounded `flatMap`, and rate buffers.**
