---
icon: lucide/network
---

# 0006: Servlet Architecture vs Spring DispatcherServlet & Web MVC Pipeline

Before building REST APIs, we must understand how HTTP requests travel from the network into your Java code. 

In this lesson, we demystify the transition from raw **Java Servlets (`HttpServlet`)** to Spring MVC's **`DispatcherServlet` (Front Controller Pattern)**, dissect the complete internal request-response pipeline, and contrast **Filters, Interceptors, and AOP**.

---

## 1. The Pre-Spring Era: Raw Java Servlets

In classic Java Enterprise applications (Java EE / Jakarta EE), the **Servlet Container** (such as Apache Tomcat or Eclipse Jetty) listens on a network port (e.g., `8080`), accepts TCP connections, parses raw HTTP text streams, and maps them to registered `HttpServlet` instances.

``` mermaid
flowchart TD
    Client["🌐 HTTP Client<br/>(Browser / Curl)"] -->|HTTP Request| Tomcat["📦 Servlet Container<br/>(Embedded Tomcat)"]
    Tomcat -->|web.xml routing| S1["OrderServlet<br/><i>/orders/*</i>"]
    Tomcat -->|web.xml routing| S2["UserServlet<br/><i>/users/*</i>"]
    Tomcat -->|web.xml routing| S3["ProductServlet<br/><i>/products/*</i>"]
```

### The Limitations of Raw Servlets:
1. **Scattered Boilerplate**: Every servlet had to manually read query parameters, parse JSON request streams using low-level I/O streams, and write response headers.
2. **Duplicate Cross-Cutting Logic**: Authentication, logging, and error handling had to be copy-pasted across dozens of servlets.
3. **Tight Coupling to Servlet API**: Testing required complex mocks of `HttpServletRequest` and `HttpServletResponse`.

---

## 2. The Spring MVC Solution: Front Controller Pattern

Spring MVC eliminates servlet sprawl by introducing a **Front Controller** pattern implemented by a single master servlet: **`DispatcherServlet`**.

Instead of registering hundreds of servlets with Tomcat, Spring registers **one** servlet mapped to `/`. The `DispatcherServlet` acts as a central coordinator, routing requests to lightweight POJO (Plain Old Java Object) controllers.

``` mermaid
flowchart TD
    Client["🌐 Client Request<br/><code>GET /api/v1/orders/42</code>"] --> FilterChain["🛡️ Servlet Filter Chain<br/>(Security, CORS, Logging)"]
    FilterChain --> DS["⚡ DispatcherServlet<br/>(Front Controller)"]
    
    DS --> HM["1. HandlerMapping<br/><i>(Finds matching Controller method)</i>"]
    HM --> DS
    
    DS --> HA["2. HandlerAdapter<br/><i>(Executes method & resolves arguments)</i>"]
    HA --> Ctrl["3. OrderController<br/><i>(Your Business Code)</i>"]
    Ctrl --> HA
    HA --> DS
    
    DS --> MC["4. HttpMessageConverter<br/><i>(Jackson converts Java Object to JSON)</i>"]
    MC --> Client["📤 HTTP Response 200 OK<br/><code>{'id': 42, 'status': 'PAID'}</code>"]
```

---

## 3. Deep Dive: The `DispatcherServlet` Internal Lifecycle

When a request arrives at `DispatcherServlet`, it executes `doDispatch(request, response)`. Here is the exact internal sequence:

``` mermaid
sequenceDiagram
    autonumber
    actor Client as 🌐 Client
    participant Tomcat as 📦 Servlet Container (Tomcat)
    participant Filter as 🛡️ Servlet Filters (OncePerRequestFilter)
    participant DS as ⚡ DispatcherServlet
    participant HM as 🗺️ HandlerMapping
    participant Interceptor as ⏱️ HandlerInterceptor
    participant HA as ⚙️ HandlerAdapter
    participant HMR as 🧩 ArgumentResolvers
    participant Ctrl as 🎮 @RestController
    participant HMC as 🔄 HttpMessageConverter (Jackson)

    Client->>Tomcat: HTTP POST /api/v1/users (JSON payload)
    Tomcat->>Filter: doFilter()
    Filter->>DS: service() -> doDispatch()
    
    DS->>HM: getHandler(request)
    HM-->>DS: HandlerExecutionChain (Controller Method + Interceptors)
    
    DS->>Interceptor: preHandle() [e.g., Latency timer start, Trace ID]
    
    DS->>HA: getHandlerAdapter(handler)
    DS->>HA: handle(request, response, handler)
    
    HA->>HMR: resolveArgument() -> Read body & Validate
    HMR->>HMC: read() [JSON -> UserRequestDTO]
    HMC-->>HA: UserRequestDTO instance
    
    HA->>Ctrl: createUser(UserRequestDTO)
    Ctrl-->>HA: UserResponseDTO instance
    
    HA->>HMC: write() [UserResponseDTO -> JSON bytes]
    HMC-->>DS: Serialized HTTP response written
    
    DS->>Interceptor: postHandle()
    DS->>Interceptor: afterCompletion() [Cleanup MDC context]
    
    DS-->>Filter: Response completed
    Filter-->>Tomcat: Chain complete
    Tomcat-->>Client: HTTP 201 Created (JSON Response)
```

### Key Components Explained:
- **`HandlerMapping`**: Inspects `@RequestMapping` annotations to locate the specific method that handles the incoming URL, HTTP method (`GET`, `POST`), and headers.
- **`HandlerExecutionChain`**: Wraps the target handler method along with all configured **`HandlerInterceptor`** instances.
- **`HandlerAdapter` (`RequestMappingHandlerAdapter`)**: Invokes the method via reflection, calling `HandlerMethodArgumentResolver` to bind `@PathVariable`, `@RequestParam`, and `@RequestBody`.
- **`HttpMessageConverter` (`MappingJackson2HttpMessageConverter`)**: Serializes Java DTOs to JSON and deserializes JSON payloads into Java objects using Jackson's `ObjectMapper`.

---

## 4. Comparing Extension Points: Filters vs Interceptors vs AOP

Understanding where your logic should execute in the request pipeline is essential for writing clean web applications:

``` mermaid
flowchart TD
    subgraph Container["Servlet Container Level"]
        F["🛡️ Servlet Filter<br/>(e.g., OncePerRequestFilter)"]
    end

    subgraph SpringMVC["Spring MVC Dispatcher Level"]
        I["⏱️ HandlerInterceptor<br/>(preHandle, postHandle)"]
    end

    subgraph CoreSpring["Spring IoC / Bean Level"]
        A["✂️ AOP Aspect<br/>(@Around on @Service)"]
    end

    F --> I --> A

    Container ~~~ SpringMVC ~~~ CoreSpring
```

| Dimension | Servlet Filter (`Filter`) | Spring Interceptor (`HandlerInterceptor`) | AOP Aspect (`@Aspect`) |
| :--- | :--- | :--- | :--- |
| **Scope Level** | Outside Spring MVC (Servlet container level) | Inside Spring MVC (around `HandlerAdapter`) | Around any Spring Bean method execution |
| **Aware of Controller?** | No (knows only raw Request / Response) | Yes (knows `HandlerMethod` reflection metadata) | Yes (knows Method signature, arguments, target bean) |
| **Context Access** | Limited Spring Bean access | Full Spring `ApplicationContext` access | Full Spring `ApplicationContext` access |
| **Ideal Use Cases** | CORS headers, TLS termination, Rate limiting, Security filter chains, Request body wrapper | Request timing, Audit logging, MDC Trace ID injection, Tenant ID extraction | Transaction management (`@Transactional`), Custom business metrics, Fine-grained authorization |

---

## 5. Hands-On: Building a Custom Request Tracking Interceptor

Let's implement a custom `HandlerInterceptor` that generates a unique `X-Trace-Id`, measures execution latency, and injects it into the SLF4J Mapped Diagnostic Context (MDC):

### Step 1: Implement `HandlerInterceptor`

```java
package com.example.demo.interceptor;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.slf4j.MDC;
import org.springframework.stereotype.Component;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.UUID;

@Component
public class RequestMetricsInterceptor implements HandlerInterceptor {

    private static final Logger log = LoggerFactory.getLogger(RequestMetricsInterceptor.class);
    private static final String START_TIME_ATTR = "requestStartTime";
    private static final String TRACE_ID_HEADER = "X-Trace-Id";

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        long startTime = System.currentTimeMillis();
        request.setAttribute(START_TIME_ATTR, startTime);

        // Extract or generate Trace ID
        String traceId = request.getHeader(TRACE_ID_HEADER);
        if (traceId == null || traceId.isBlank()) {
            traceId = UUID.randomUUID().toString().substring(0, 8);
        }
        
        MDC.put("traceId", traceId);
        response.setHeader(TRACE_ID_HEADER, traceId);

        if (handler instanceof HandlerMethod handlerMethod) {
            log.info("▶️ [START] {} {} -> {}.{}()",
                    request.getMethod(), request.getRequestURI(),
                    handlerMethod.getBeanType().getSimpleName(),
                    handlerMethod.getMethod().getName());
        }
        return true; // Return true to continue execution chain
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        Long startTime = (Long) request.getAttribute(START_TIME_ATTR);
        long duration = (startTime != null) ? (System.currentTimeMillis() - startTime) : 0;

        log.info("⏹️ [END] {} {} | Status: {} | Duration: {}ms",
                request.getMethod(), request.getRequestURI(), response.getStatus(), duration);

        // Always clean up MDC to prevent thread pool memory leaks!
        MDC.clear();
    }
}
```

### Step 2: Register the Interceptor via `WebMvcConfigurer`

```java
package com.example.demo.config;

import com.example.demo.interceptor.RequestMetricsInterceptor;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@RequiredArgsConstructor
public class WebMvcConfig implements WebMvcConfigurer {

    private final RequestMetricsInterceptor requestMetricsInterceptor;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(requestMetricsInterceptor)
                .addPathPatterns("/api/**")       // Intercept all API requests
                .excludePathPatterns("/actuator/**", "/swagger-ui/**"); // Skip health & docs
    }
}
```

---

## 6. Spring Boot 3 vs Spring Boot 4: Servlet Pipeline & Web Engine Evolution

``` mermaid
flowchart TD
    subgraph SB3["Spring Boot 3.x (Jakarta EE 10)"]
        Tomcat10["Tomcat 10.1 / Servlet 6.0"]
        PoolThreads["Platform Worker Thread Pool (200 threads)"]
        OptInLoom["Opt-in Virtual Threads via Property"]
    end

    subgraph SB4["Spring Boot 4.x (Jakarta EE 11)"]
        Tomcat11["Tomcat 11 / Servlet 6.1"]
        DefaultLoom["Virtual Threads by Default (Unbounded I/O)"]
        HTTP3["Native HTTP/3 & QUIC Support"]
    end

    SB3 ==>|Concurrency Revolution| SB4
```

### Key Differences & Configuration Comparison

| Web Engine Capability | Spring Boot 3.x | Spring Boot 4.x |
| :--- | :--- | :--- |
| **Servlet Specification** | Jakarta Servlet 6.0 (Jakarta EE 10). | **Jakarta Servlet 6.1 (Jakarta EE 11)** with enhanced non-blocking buffer transfers. |
| **Default Concurrency Model** | Traditional 200-worker Platform Thread Pool (`server.tomcat.threads.max=200`). | **Virtual Threads Enabled by Default**: Each request runs on a lightweight Virtual Thread. |
| **HTTP Protocols** | HTTP/1.1 and HTTP/2 (TLS required). | **HTTP/3 & QUIC Native Support** configurable directly via `server.http3.enabled=true`. |
| **DispatcherServlet Dispatch** | Standard async Servlet 3.0 `AsyncContext`. | **Cooperative Loom Dispatch**: Direct synchronous-style non-blocking execution without reactive callbacks. |

---

## 7. Primary Sources & Further Reading

- [Spring Framework Reference: Web MVC Architecture](https://docs.spring.io/spring-framework/reference/web/webmvc.html) — The official deep dive into `DispatcherServlet` and handler execution.
- [Jakarta Servlet Specification](https://jakarta.ee/specifications/servlet/) — Standard defining the Servlet container lifecycle and filter chains.
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html) — Authoritative HTTP standards for methods, status codes, and headers.

---

## 8. Knowledge Check & Retrieval Practice

??? question "Question 1: What is the primary role of the `DispatcherServlet` in Spring MVC?"
    **Answer**: It acts as the Front Controller, centralizing request routing, adapter invocation, argument binding, and response serialization across all endpoints.

??? question "Question 2: If you need to inspect the target Controller method's annotations before execution, should you use a Filter or a HandlerInterceptor?"
    **Answer**: Use a `HandlerInterceptor`, because its `preHandle()` method receives the `handler` object (casted to `HandlerMethod`), providing full reflection metadata.

??? question "Question 3: Why must `MDC.clear()` be called in `afterCompletion()` of an interceptor?"
    **Answer**: Servlet containers use thread pools (`worker-threads`). Failing to clear the MDC leaks context data and causes request pollution across subsequent threads.

---

## 🧭 Navigation & Next Steps

| ⬅️ Previous | 📋 Catalog | ➡️ Next |
| :--- | :---: | ---: |
| [⬅️ **0005: Spring Profiles & Multi-Environment Configuration**](0005-spring-profiles-and-environments.md) | [**All Lessons**](index.md) | [➡️ **0007: Building RESTful CRUD APIs with Controllers**](0007-building-restful-crud-apis.md) |

💬 *Have any questions about the DispatcherServlet pipeline? Ask anytime!*
