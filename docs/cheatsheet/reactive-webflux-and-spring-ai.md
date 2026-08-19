---
icon: lucide/file-code
---

# Reactive WebFlux and Spring AI cheatsheet

Reference card for Project Reactor, Spring WebFlux, R2DBC non-blocking persistence, Server-Sent Events, Spring AI `ChatClient`, vector stores, and Model Context Protocol tool servers.

---

## 1. Project Reactor core operators

```java
// Transform and async flatten
Mono<UserDto> dtoMono = userMono.map(UserDto::from);
Flux<Order> ordersFlux = userFlux.flatMap(user -> orderClient.getOrders(user.id()), 16); // Bounded flatMap

// Parallel zip and error recovery
Mono<Dashboard> dashboardMono = Mono.zip(userMono, statsMono)
        .map(tuple -> new Dashboard(tuple.getT1(), tuple.getT2()))
        .onErrorResume(ServiceException.class, ex -> fallbackService.getDegradedDashboard())
        .retryWhen(Retry.backoff(3, Duration.ofMillis(500)));

// Thread switching (offloading blocking I/O)
Mono<byte[]> fileMono = Mono.fromCallable(() -> Files.readAllBytes(path))
        .subscribeOn(Schedulers.boundedElastic())
        .publishOn(Schedulers.parallel());
```

---

## 2. Spring WebFlux controller and SSE streaming

```java
// Streaming SSE endpoint
@GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
public Flux<ServerSentEvent<StockEvent>> streamPrices() {
    return stockService.getPriceFlux()
            .map(data -> ServerSentEvent.<StockEvent>builder()
                    .event("price-tick")
                    .data(data)
                    .retry(Duration.ofSeconds(3))
                    .build());
}

// Functional router function
@Bean
public RouterFunction<ServerResponse> routes(ProductHandler handler) {
    return route()
            .GET("/api/v1/products/{id}", handler::getProduct)
            .POST("/api/v1/products", handler::createProduct)
            .build();
}
```

---

## 3. R2DBC and reactive Redis cache-aside

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

## 4. Spring AI `ChatClient` and structured output

```java
// 1. Fluent ChatClient with structured JSON record
SentimentResult result = chatClient.prompt()
        .user(u -> u.text("Analyze sentiment: {text}")
                .param("text", reviewText)
                .param("format", outputConverter.getFormat()))
        .call()
        .entity(new BeanOutputConverter<>(SentimentResult.class));

// 2. Real-time token streaming with Project Reactor
Flux<String> tokenStream = chatClient.prompt()
        .user("Explain quantum computing in 3 sentences")
        .stream()
        .content();
```

---

## 5. Spring AI RAG with vector stores and advisors

```java
// Ingest documents into pgvector
TokenTextSplitter splitter = new TokenTextSplitter(800, 100, 5, 10000, true);
vectorStore.accept(splitter.apply(rawDocuments));

// Query with RAG advisor
ChatClient ragClient = builder
        .defaultAdvisors(new QuestionAnswerAdvisor(vectorStore, SearchRequest.defaults().withTopK(4)))
        .build();

String answer = ragClient.prompt().user("What is our refund policy?").call().content();
```

---

## 6. Model Context Protocol tool definition

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

## Navigation and cheatsheet index

| Previous | Cheatsheet index | Next |
| :--- | :---: | ---: |
| [**Microservices, Kubernetes, and cloud CI/CD cheatsheet**](microservices-kubernetes-and-cloud-cicd.md) | [**All cheatsheets**](index.md) | All cheatsheets completed |
