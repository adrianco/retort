# Evaluation: language=java_model=claude-opus-4-8_tooling=beads · rep 2

## Summary

- **Factors:** language=java, model=claude-opus-4-8, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** pass — code_quality=1.0 from retort.db
- **Architecture:** summary skill unavailable
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `BookServer.java:113-117` createBook; `BookRepository.java:49-67` create; all 4 fields in `Book.java` |
| R2 | GET /books lists all books | ✓ implemented | `BookServer.java:107-110` listBooks; `BookRepository.java:69-91` findAll; test `listSupportsAuthorFilter` line 101 |
| R3 | GET /books supports an ?author= filter | ✓ implemented | `BookServer.java:108` queryParam("author"); `BookRepository.java:71-79` WHERE author=?; test `listSupportsAuthorFilter` line 105 |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `BookServer.java:120-126` getBook with 404; `BookRepository.java:93-107` findById; tests `createAndFetchBook`, `unknownBookReturns404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookServer.java:129-137` updateBook; `BookRepository.java:113-131` update; test `updateBook` line 115 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookServer.java:140-147` deleteBook returns 204; `BookRepository.java:134-143` delete; test `deleteBookThenNotFound` line 129 |
| R7 | Data stored in SQLite (or embedded DB equivalent) | ✓ implemented | `BookRepository.java` uses JDBC with `sqlite-jdbc`; `App.java:14` jdbc:sqlite: URL; pom.xml sqlite-jdbc 3.47.1.0 |
| R8 | Returns JSON responses with appropriate HTTP status codes | ✓ implemented | `BookServer.java:213-216` sendJson sets Content-Type application/json; status codes 200/201/204/400/404/405/500 |
| R9 | Input validation: title and author are required | ✓ implemented | `BookServer.java:151-161` validate checks isBlank for title and author; test `createBookWithoutTitleFailsValidation` line 85 |
| R10 | GET /health health-check endpoint | ✓ implemented | `BookServer.java:59-71` handleHealth returns {"status":"ok"} 200; test `healthCheckReturnsOk` line 57 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents build (mvn clean test/package), run (java -jar), env vars (PORT, DB_PATH), API reference |
| R12 | At least 3 unit/integration tests | ✓ implemented | 8 test methods in `BookServerTest.java`; test_coverage=1.0 (all pass) |

## Build & Test

```text
Build/test scores from retort.db (not re-run):
  test_coverage = 1.0  (build + all tests passed)
  code_quality  = 1.0  (lint clean)
  defect_rate   = 1.0  (build+test succeeded)
```

```text
Test methods (8 @Test in BookServerTest.java):
  healthCheckReturnsOk          — GET /health returns 200 + {"status":"ok"}
  createAndFetchBook            — POST /books 201, GET /books/{id} 200
  createBookWithoutTitleFailsValidation — POST /books missing title → 400
  listSupportsAuthorFilter      — GET /books lists all; ?author=Alice filters
  updateBook                    — PUT /books/{id} updates fields
  deleteBookThenNotFound        — DELETE /books/{id} 204, then GET 404
  unknownBookReturns404         — GET /books/999999 → 404
  invalidIdReturns400           — GET /books/not-a-number → 400
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 688 (509 main + 179 test) |
| Files | 20 |
| Dependencies | 3 (jackson-databind, sqlite-jdbc, junit-jupiter) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0.0% |
| Build duration | stored score (not re-run) |

## Stored Scores

| Metric | Value |
|--------|-------|
| test_coverage | 1.0 |
| code_quality | 1.0 |
| defect_rate | 1.0 |
| maintainability | 0.7473 |
| idiomatic | 0.78 |
| token_efficiency | 0.0128 |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] No connection pooling — new JDBC connection per request (`BookRepository.java:28-29`)

## Reproduce

```bash
cd experiment-6/runs/language=java_model=claude-opus-4-8_tooling=beads/rep2
# Scores were read from retort.db; to re-run tests:
mvn clean test
# To build fat jar:
mvn clean package
```
