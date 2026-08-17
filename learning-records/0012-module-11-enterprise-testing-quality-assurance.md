# Learning Record 0012: Module 11 — Enterprise Testing & Quality Assurance Completed

- **Date**: 2026-08-17
- **Module**: Module 11: Enterprise Testing & Quality Assurance (JUnit 5, Mockito, MockMvc, Testcontainers)
- **Status**: Completed

## Concepts Mastered

1. **JUnit 5 (Jupiter) & AssertJ**:
   - Modern test lifecycle hooks (`@BeforeAll`, `@BeforeEach`, `@Test`, `@AfterEach`, `@AfterAll`).
   - Parameterized test execution with `@ParameterizedTest`, `@CsvSource`, `@ValueSource`, and `@MethodSource`.
   - Expressive assertion pipelines with AssertJ (`assertThat()`, `.extracting()`, `.usingRecursiveComparison()`, `assertThatThrownBy()`).
   - BDD-style hierarchical testing using `@Nested` test classes and `@DisplayName`.

2. **Mocking with Mockito**:
   - Isolating domain services from external collaborators using `@ExtendWith(MockitoExtension.class)`, `@Mock`, and `@InjectMocks`.
   - Pre-programming stub responses with `when(...).thenReturn(...)` and simulating faults with `doThrow(...)`.
   - Interaction verification with `verify(mock, times(1)).method()`, `verifyNoMoreInteractions()`, and capturing internal invocation arguments using `ArgumentCaptor<T>`.
   - Mocking evolution: transitioning from deprecated `@MockBean` to core Spring Framework 6.2+ `@MockitoBean`.

3. **REST Web Slicing with `@WebMvcTest` & `MockMvc`**:
   - Bootstrapping focused web slices in under 1 second without initializing database or background worker layers.
   - Performing in-memory HTTP requests across the complete `DispatcherServlet` pipeline.
   - Asserting HTTP status codes, headers, and JSON body structures using Jayway `jsonPath()` and Hamcrest matchers.
   - Testing Bean Validation (`@Valid`) constraints and `@RestControllerAdvice` RFC 7807/9457 `ProblemDetails` error contracts.

4. **Database Integration Testing with Testcontainers**:
   - Avoiding the in-memory H2 database fallacy and testing against genuine containerized PostgreSQL instances.
   - Automatic container configuration via Spring Boot 3.1+ `@ServiceConnection` (eliminating manual `@DynamicPropertySource` declarations).
   - Singleton container pattern to share running database containers across the entire test suite and eliminate repetitive startup overhead.
   - `@DataJpaTest` slicing with real PostgreSQL containers.

## Artifacts Produced

- Lessons: `0048`, `0049`, `0050`, `0051` (with Spring Boot 3 vs 4 comparisons and vertical Mermaid diagrams).
- Cheatsheet: `docs/cheatsheet/enterprise-testing-and-testcontainers.md`.
- Debugging Guide: `docs/debugging/spring-boot-testing-and-testcontainers-pitfalls.md`.
- Interview Questions: 10 high-signal testing questions in `docs/interview/index.md`.
- Glossary: Added definitions for JUnit 5, AssertJ, Mockito, MockMvc, `@WebMvcTest`, Testcontainers, `@DynamicPropertySource`, and `@ServiceConnection`.
