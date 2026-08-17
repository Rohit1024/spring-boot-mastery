---
icon: lucide/file-code
---

# Reactive WebFlux & Spring AI Cheatsheet

A production reference card for Project Reactor, Spring WebFlux, R2DBC non-blocking persistence, Server-Sent Events (SSE), Spring AI `ChatClient`, RAG Vector Stores, and Model Context Protocol (MCP) tool servers.

---

## 1. Project Reactor Core Operators Cheat Sheet

```java
// Transform & Async Flatten
Mono<UserDto> dtoMono = userMono.map(UserDto::from);
Flux<Order> ordersFlux = userFlux.flatMap(user -> orderClient.getOrders(user.id()), 16); // Bounded flatMap

// Parallel Zip & Error Recovery
Mono<Dashboard> dashboardMono = Mono.zip(userMono, statsMono)
        .map(tuple -> new Dashboard(tuple.getT1(), tuple.getT2()))
        .onErrorResume(ServiceException.class, ex -> fallbackService.getDegradedDashboard())
        .retryWhen(Retry.backoff(3, Duration.ofMillis(500)));

// Thread Switching (Offloading Blocking I/O)
Mono<byte[]> fileMono = Mono.fromCallable(() -> Files.readAllBytes(path))
        .subscribeOn(Schedulers.boundedElastic())
        .publishOn(Schedulers.parallel());
```

---

## 2. Spring WebFlux Controller & SSE Streaming

```java
// Streaming SSE Endpoint
@GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<ServerSentEvent<StockEvent>> streamPrices() {
    return stockService.getPriceFlux()
            .map(data -> ServerSentEvent.<StockEvent>builder()
                    .event("price-tick")
                    .data(data)
                    .retry(Duration.ofSeconds(3))
                    .build());
}

// Functional Router Function
@Bean
public RouterFunction<ServerResponse> routes(ProductHandler handler) {
    return route()
            .GET("/api/v1/products/{id}", handler::getProduct)
            .POST("/api/v1/products", handler::createProduct)
            .build();
}
```

---

## 3. R2DBC & Reactive Redis Cache-Aside

```java
public Mono<Product> getProduct(Long id) {
    String key = "product:" + id;
    return reactiveRedisTemplate.opsForValue().get(key)
            .switchIfEmpty(
                    r2dbcRepository.findById(id)
                            .flatMap(p -> reactiveRedisTemplate.opsForValue()
                                    .set(key, p, Duration.ofMinutes(10))
                                    .thenReturn(p))
            );
}
```

---

## 4. Spring AI `ChatClient` & Structured Output

```java
// 1. Fluent ChatClient with Structured JSON Record
SentimentResult result = chatClient.prompt()
        .user(u -> u.text("Analyze sentiment: {text}")
                .param("text", reviewText)
                .param("format", outputConverter.getFormat()))
        .call()
        .entity(new BeanOutputConverter<>(SentimentResult.class));

// 2. Real-Time Token Streaming with Project Reactor
Flux<String> tokenStream = chatClient.prompt()
        .user("Explain quantum computing in 3 sentences")
        .stream()
        .content();
```

---

## 5. Spring AI RAG with Vector Stores & Advisors

```java
// Ingest Documents into pgvector
TokenTextSplitter splitter = new TokenTextSplitter(800, 100, 5, 10000, true);
vectorStore.accept(splitter.apply(rawDocuments));

// Query with RAG Advisor
ChatClient ragClient = builder
        .defaultAdvisors(new QuestionAnswerAdvisor(vectorStore, SearchRequest.defaults().withTopK(4)))
        .build();

String answer = ragClient.prompt().user("What is our refund policy?").call().content();
```

---

## 6. Model Context Protocol (MCP) Tool Definition

```java
@Component
public class InventoryMcpTools {

    @Tool(name = "check_warehouse_stock", description = "Query available inventory count for a given SKU")
    public int checkStock(@ToolParam(description = "Product SKU code") String sku) {
        return inventoryService.getStock(sku);
    }
}
```

---

## 🧭 Navigation & Cheatsheet Index

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **Microservices, Kubernetes & Cloud CI/CD Cheatsheet**](microservices-kubernetes-and-cloud-cicd.md) | [**All Cheatsheets**](index.md) | 🏆 **All Cheatsheets Completed!** |
