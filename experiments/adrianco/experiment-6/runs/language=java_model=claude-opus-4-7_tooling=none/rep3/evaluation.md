# Evaluation: language=java_model=claude-opus-4-7_tooling=none · rep 3

## Summary

- **Factors:** language=java, model=claude-opus-4-7, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** pass — code_quality=1.0 from retort.db
- **Architecture:** summary skill not invoked (standalone evaluation)
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `App.java:99` createBook, `BookRepository.java:43` create; test `BookApiTest.java:54` |
| R2 | GET /books lists all books | ✓ implemented | `App.java:93` listBooks, `BookRepository.java:64` findAll; test `BookApiTest.java:64` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `App.java:94` queryParam("author"), `BookRepository.java:65-67` WHERE author = ?; test `BookApiTest.java:99` filterByAuthor |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `App.java:114` getBook with 404; tests `BookApiTest.java:70`, `BookApiTest.java:117` getMissingBookReturns404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `App.java:123` updateBook, `BookRepository.java:93` update; test `BookApiTest.java:74` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `App.java:142` deleteBook returns 204; test `BookApiTest.java:81` |
| R7 | Data stored in SQLite | ✓ implemented | `BookRepository.java:16` uses jdbc:sqlite:, `pom.xml:27` sqlite-jdbc dependency |
| R8 | Returns JSON with appropriate HTTP status codes | ✓ implemented | `App.java:183` sendJson sets Content-Type application/json; uses 200/201/204/400/404/405 |
| R9 | Input validation: title and author required | ✓ implemented | `App.java:152-155` validate checks null/blank; test `BookApiTest.java:89` rejectsBookWithoutRequiredFields |
| R10 | GET /health health-check endpoint | ✓ implemented | `App.java:57` handleHealth returns {"status":"ok"}; test `BookApiTest.java:46` healthEndpointReturnsOk |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents build (mvn package), run (java -cp), and all endpoints |
| R12 | At least 3 unit/integration tests | ✓ implemented | 5 @Test methods in `BookApiTest.java`: healthEndpointReturnsOk, createListGetUpdateDeleteBook, rejectsBookWithoutRequiredFields, filterByAuthor, getMissingBookReturns404 |

## Build & Test

```text
Build/test scores from retort.db (not re-run):
  test_coverage = 1.0  (build + all tests passed)
  code_quality  = 1.0
  defect_rate   = 1.0
```

```text
5 @Test methods, 0 skipped, 0 disabled.
Tests exercise: health check, full CRUD lifecycle, validation errors, author filter, 404 on missing book.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 510 (4 Java files) |
| Files (excl. build artifacts) | 10 |
| Dependencies | 3 (jackson-databind, sqlite-jdbc, junit-jupiter) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | (from retort.db — not re-timed) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Uses JDK built-in HttpServer instead of a web framework — acceptable, no framework mandated

## Reproduce

```bash
cd experiment-6/runs/language=java_model=claude-opus-4-7_tooling=none/rep3
cat stack.json
cat TASK.md
# Scores read from retort.db (test_coverage=1.0, code_quality=1.0, defect_rate=1.0)
# Source inspection: 4 Java files in src/
grep -c "@Test" src/test/java/com/example/books/BookApiTest.java  # 5 tests
grep -rE "@Disabled|@Ignore" src/ --include="*.java"              # 0 skipped
```
