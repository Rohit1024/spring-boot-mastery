# Spring Core & Annotations Cheatsheet

A quick reference guide for core Spring Framework annotations and container concepts.

## Stereotype Annotations

| Annotation | Layer / Purpose | Notes |
| :--- | :--- | :--- |
| `@Component` | General-purpose managed Spring Bean | Root annotation for all stereotypes |
| `@Service` | Service / Business Logic Layer | Semantic alias for `@Component` |
| `@Repository` | Data Access / DAO Layer | Translates DB exceptions into Spring `DataAccessException` |
| `@Controller` | Web Layer (Spring MVC) | Returns view templates or handles web navigation |
| `@RestController`| Web Layer (REST API) | Combines `@Controller` + `@ResponseBody` |
| `@Configuration` | Java Config class defining `@Bean`s | Proxied via CGLIB by default (`proxyBeanMethods = true`) |
| `@Bean` | Method-level Bean declaration | Explicitly produces a Spring Bean into `ApplicationContext` |

## Dependency Injection Annotations

| Annotation | Usage |
| :--- | :--- |
| `@Autowired` | Injects matching bean by type (Optional on single constructor since Spring 4.3) |
| `@Qualifier("beanName")` | Resolves ambiguity when multiple beans of the same type exist |
| `@Primary` | Designates default bean when multiple candidates exist |
| `@Value("${property.key:defaultValue}")` | Injects values from `application.properties` or environment |

## Lifecycle Annotations

| Annotation | Execution Phase |
| :--- | :--- |
| `@PostConstruct` | Runs immediately after dependency injection is complete |
| `@PreDestroy` | Runs immediately before the bean is destroyed / context shuts down |
| `@Scope("prototype")` | Specifies scope: `singleton` (default), `prototype`, `request`, `session` |
| `@Lazy` | Defers bean initialization until first access |

## Quick Snippet: Clean Constructor Injection Pattern

```java
@Service
public class PaymentProcessingService {

    private final PaymentGateway gateway;
    private final NotificationClient notificationClient;

    // Single constructor: @Autowired is automatically inferred
    public PaymentProcessingService(
            @Qualifier("stripeGateway") PaymentGateway gateway,
            NotificationClient notificationClient) {
        this.gateway = gateway;
        this.notificationClient = notificationClient;
    }
}
```

---

## 🧭 Navigation

| ⬅️ Previous | 📋 Cheatsheet Index | ➡️ Next |
| :--- | :---: | ---: |
| *(First Cheatsheet)* | [**All Cheatsheets**](index.md) | [➡️ **Spring Web MVC & REST Cheatsheet**](spring-web-mvc-rest.md) |

