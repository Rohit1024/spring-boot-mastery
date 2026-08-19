# Spring Core and annotations cheatsheet

Reference guide for core Spring Framework annotations and container concepts.

## Stereotype annotations

| Annotation | Layer and purpose | Notes |
| :--- | :--- | :--- |
| `@Component` | Managed Spring bean | Root annotation for all stereotypes |
| `@Service` | Service and business logic layer | Semantic alias for `@Component` |
| `@Repository` | Data access and DAO layer | Translates DB exceptions into Spring `DataAccessException` |
| `@Controller` | Web layer (Spring MVC) | Returns view templates or handles web navigation |
| `@RestController`| Web layer (REST API) | Combines `@Controller` + `@ResponseBody` |
| `@Configuration` | Java configuration class defining beans | Proxied via CGLIB by default (`proxyBeanMethods = true`) |
| `@Bean` | Method-level bean declaration | Explicitly produces a Spring bean into `ApplicationContext` |

## Dependency injection annotations

| Annotation | Usage |
| :--- | :--- |
| `@Autowired` | Injects matching bean by type. Optional on single constructor since Spring 4.3. |
| `@Qualifier("beanName")` | Resolves ambiguity when multiple beans of the same type exist. |
| `@Primary` | Designates default bean when multiple candidates exist. |
| `@Value("${property.key:defaultValue}")` | Injects values from `application.properties` or environment. |

## Lifecycle annotations

| Annotation | Execution phase |
| :--- | :--- |
| `@PostConstruct` | Runs immediately after dependency injection is complete. |
| `@PreDestroy` | Runs immediately before the bean is destroyed or context shuts down. |
| `@Scope("prototype")` | Specifies scope: `singleton` (default), `prototype`, `request`, `session`. |
| `@Lazy` | Defers bean initialization until first access. |

## Constructor injection pattern

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

## Navigation and cheatsheet index

| Previous | Cheatsheet index | Next |
| :--- | :---: | ---: |
| First cheatsheet | [**All cheatsheets**](index.md) | [**Spring Web MVC and REST APIs cheatsheet**](spring-web-mvc-rest.md) |
