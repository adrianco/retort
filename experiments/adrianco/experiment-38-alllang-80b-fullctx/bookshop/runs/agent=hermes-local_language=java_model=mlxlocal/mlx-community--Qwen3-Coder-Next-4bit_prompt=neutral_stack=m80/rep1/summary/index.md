# Architecture Summary — book-api (Java / Spring Boot)

`run-summary` skill is not registered as an invocable skill in this session; this is a
hand-written stand-in.

## Stack
Spring Boot 3.2.5, Spring Data JPA, Hibernate. Persistence: SQLite (`jdbc:sqlite:books.db`)
in production; H2 in-memory for tests. Java 17 target (built here on JDK 26). Maven build.

## Modules (`src/main/java/com/bookapi/`)
- `BookApiApplication` — Spring Boot entry point.
- `controller/BookController` — REST layer, `@RequestMapping("/api/books")`. Endpoints:
  POST, GET (with `?author=` filter), GET `/{id}`, PUT `/{id}`, DELETE `/{id}`, GET `/health`
  (resolves to `/api/books/health`). Maps entity↔`BookResponse`.
- `service/BookService` — transactional business layer over the repository; throws
  `ResourceNotFoundException` on missing ids.
- `service/ResourceNotFoundException` — plain `RuntimeException`, **no** `@ResponseStatus`
  and **no** `@ControllerAdvice` anywhere → not-found maps to HTTP 500, not 404.
- `repository/BookRepository` — `JpaRepository<Book,Long>` with derived `findByAuthor`.
- `entity/Book` — JPA entity, `@NotBlank`/`@Size` bean-validation constraints (also enforced
  on persist by Hibernate).
- `dto/BookRequest` (validated with `@Valid` in the controller → 400 on bad input),
  `dto/BookResponse`.

## Flow
HTTP → `BookController` (`@Valid` request validation) → `BookService` (`@Transactional`) →
`BookRepository` → Hibernate → SQLite/H2. Responses serialized as JSON via Jackson.

## Test topology (`src/test/java/com/bookapi/`)
- `dto/BookRequestTest` — 6 pure bean-validation unit tests (all pass).
- `repository/BookRepositoryTest` — 6 `@SpringBootTest @Transactional` tests (1 errors:
  the over-length-entity test expects a save that bean validation rejects).
- `controller/BookControllerIntegrationTest` — 12 MockMvc tests, **not** transactional and
  never resets the DB, so IDs/state leak between methods (3 order-dependent failures + 4
  not-found errors from the missing 404 handler).

See `../evaluation.md` and `../findings.jsonl` for the conformance assessment.
