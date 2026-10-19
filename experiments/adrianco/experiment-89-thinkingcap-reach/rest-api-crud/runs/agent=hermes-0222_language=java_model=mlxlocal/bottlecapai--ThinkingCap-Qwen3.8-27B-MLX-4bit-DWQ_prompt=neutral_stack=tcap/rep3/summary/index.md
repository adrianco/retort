# Architecture Summary: book-api (Java / Spring Boot / SQLite)

A single-module Maven Spring Boot 3.5 service (Java 21+) implementing a CRUD REST API
for a book collection, persisted in SQLite via Spring `JdbcTemplate`.

## Modules

| File | Role |
|------|------|
| `BookApiApplication.java` | Spring Boot entry point (`@SpringBootApplication`). |
| `BookController.java` | `/books` REST endpoints: POST/GET(list)/GET(id)/PUT/DELETE. |
| `HealthController.java` | `GET /health` → `{"status":"ok"}`. |
| `BookRepository.java` | SQLite persistence via `JdbcTemplate`; creates schema at `@PostConstruct`. |
| `Book.java` | Immutable domain record `(id, title, author, year, isbn)`. |
| `BookRequest.java` | Request DTO record; `@JsonIgnoreProperties(ignoreUnknown=true)`. |
| `Validation.java` | Required-field validation (title/author non-blank). |
| `ValidationException.java` / `BookNotFoundException.java` | Domain exceptions. |
| `GlobalExceptionHandler.java` | `@RestControllerAdvice` mapping exceptions → JSON `{"error":...}` + status. |

## Request flow

`BookController` → `Validation.validateOrThrow` (POST/PUT) → `BookRepository`
(JdbcTemplate SQL) → `Book` record → JSON via Jackson. Errors propagate to
`GlobalExceptionHandler`, which emits the correct status (201/200/204/400/404).

## Persistence

`spring.datasource.url=jdbc:sqlite:${BOOKS_DB:books.db}`, `sqlite-jdbc` driver.
Schema (`books` table, autoincrement id) created idempotently on startup.
Tests point the datasource at a temporary `target/test-books.db` via
`@DynamicPropertySource` and truncate the table before each test.

## Tests

`BookApiIntegrationTest` — 19 `@SpringBootTest` + `MockMvc` integration tests
exercising every endpoint against a real SQLite file. No skipped/disabled tests.
