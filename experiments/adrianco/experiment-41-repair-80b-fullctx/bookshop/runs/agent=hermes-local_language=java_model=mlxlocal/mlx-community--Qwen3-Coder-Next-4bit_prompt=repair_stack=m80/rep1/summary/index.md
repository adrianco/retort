# Architecture Summary — book-api (Java / Spring Boot)

`run-summary` skill is not registered as an invocable skill in this session; this is a
hand-written stand-in. **Updated after the `repair` attempt** — the earlier version of this
file described the pre-repair code.

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
- `service/ResourceNotFoundException` — plain `RuntimeException`. The `repair` added
  `handler/GlobalExceptionHandler` (`@ControllerAdvice`) mapping it to **404** (fixing the
  pre-repair 500), plus a 400 handler for `MethodArgumentNotValidException`.
- `repository/BookRepository` — `JpaRepository<Book,Long>` with derived `findByAuthor`.
- `entity/Book` — JPA entity, `@NotBlank`/`@Size` bean-validation constraints (also enforced
  on persist by Hibernate).
- `dto/BookRequest` (validated with `@Valid` in the controller → 400 on bad input),
  `dto/BookResponse`.

## Flow
HTTP → `BookController` (`@Valid` request validation) → `BookService` (`@Transactional`) →
`BookRepository` → Hibernate → SQLite/H2. Responses serialized as JSON via Jackson.

## Test topology (`src/test/java/com/bookapi/`) — post-repair, 19/24 pass
- `dto/BookRequestTest` — 6 pure bean-validation unit tests (all pass).
- `repository/BookRepositoryTest` — 6 `@SpringBootTest @Transactional` tests.
  `testBookValidationConstraints` expects `save()` to throw `ConstraintViolationException`,
  but validation fires on flush/commit (rolled back), so it does not fire → fails.
- `controller/BookControllerIntegrationTest` — 12 MockMvc tests, now `@Transactional`. The
  repair's `GlobalExceptionHandler` fixes the not-found paths (404), but tests that assert an
  absolute id / `Location: /api/books/1` (create, get-by-id, update, delete) still fail
  because the shared H2 IDENTITY sequence is not reset by rollback.

See `../evaluation.md` and `../findings.jsonl` for the conformance assessment.
