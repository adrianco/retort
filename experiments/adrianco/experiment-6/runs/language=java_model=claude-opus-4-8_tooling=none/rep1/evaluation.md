# Evaluation: language=java_model=claude-opus-4-8_tooling=none · rep 1

## Summary

- **Factors:** language=java, model=claude-opus-4-8, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — via `mvn test` (includes compile + test), BUILD SUCCESS
- **Lint:** unavailable — no separate lint step; code_quality derived from build success
- **Architecture:** summary skill not invoked (standalone evaluation)
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `BookController.java:30` — `@PostMapping` accepts `BookRequest` with all four fields, persists via `repository.save()` |
| R2 | GET /books lists all books | ✓ implemented | `BookController.java:37` — `@GetMapping` returns `repository.findAll()` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookController.java:38-39` — checks `author` param, delegates to `repository.findByAuthorIgnoreCase(author)` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `BookController.java:44-46` — `@GetMapping("/{id}")` with 404 via `BookNotFoundException` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookController.java:49-56` — `@PutMapping("/{id}")` updates all fields and saves |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookController.java:59-65` — `@DeleteMapping("/{id}")` with existence check, returns 204 |
| R7 | Data stored in SQLite (or embedded DB equivalent) | ✓ implemented | `pom.xml:39` H2 dependency; `application.properties` uses `jdbc:h2:file:./data/books` for persistent embedded storage |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `BookController.java` returns 201 (create), 200 (read/update), 204 (delete); `GlobalExceptionHandler.java` returns 400/404 with JSON bodies |
| R9 | Input validation: title and author required | ✓ implemented | `BookRequest.java:10-11` — `@NotBlank` on title and author; `GlobalExceptionHandler.java:24` handles `MethodArgumentNotValidException` |
| R10 | GET /health endpoint | ✓ implemented | `HealthController.java:11-14` — returns `{"status": "UP"}` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 133 lines, documents setup, build, run, API endpoints, examples, and project layout |
| R12 | At least 3 unit/integration tests | ✓ implemented | `BookControllerTest.java` — 6 `@SpringBootTest` integration tests: create (201), validation (400), list+filter, CRUD lifecycle, 404, health |

## Build & Test

```text
mvn test
...
Tests run: 6, Failures: 0, Errors: 0, Skipped: 0, Time elapsed: 2.104 s -- in com.example.bookcollection.BookControllerTest
Tests run: 6, Failures: 0, Errors: 0, Skipped: 0
BUILD SUCCESS
```

Note: retort.db was inaccessible (error 14); test results obtained by running `mvn test` directly as fallback.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 412 (283 main + 129 test) |
| Files | 18 |
| Dependencies | 5 (spring-boot-starter-web, spring-boot-starter-data-jpa, spring-boot-starter-validation, h2, spring-boot-starter-test) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0.0% |
| Build duration | ~2s (test phase) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Uses H2 instead of SQLite (acceptable embedded DB equivalent per TASK.md allowance)

## Reproduce

```bash
cd experiment-6/runs/language=java_model=claude-opus-4-8_tooling=none/rep1
cat stack.json
cat TASK.md
mvn test
find src -name "*.java" -exec wc -l {} +
```
