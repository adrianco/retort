# Evaluation: language=java_model=claude-opus-4-7_tooling=none · rep 1

## Summary

- **Factors:** language=java, model=claude-opus-4-7, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** pass — code_quality=1.0 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `App.java:42,56-72` createBook route; `BookDao.java:39-57` insert; `BookApiTest.java:69` test |
| R2 | GET /books lists all books | ✓ implemented | `App.java:43,74-77` listBooks route; `BookDao.java:59-79` findAll; `BookApiTest.java:93` test |
| R3 | GET /books supports ?author= filter | ✓ implemented | `App.java:75` queryParam("author"); `BookDao.java:61-66` WHERE author=?; `BookApiTest.java:93-107` test |
| R4 | GET /books/{id} returns single book | ✓ implemented | `App.java:44,79-86` getBook with 404; `BookApiTest.java:111-118,134-137` tests |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `App.java:45,89-109` updateBook with validation+404; `BookApiTest.java:120-122` test |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `App.java:46,111-118` deleteBook returns 204/404; `BookApiTest.java:124-129` test |
| R7 | Data stored in SQLite | ✓ implemented | `BookDao.java` uses JDBC sqlite; `pom.xml:36-39` sqlite-jdbc dependency; tests use temp .db file |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 create (`App.java:71`), 200 get/list/update, 204 delete (`App.java:117`), 400 validation (`App.java:67`), 404 missing (`App.java:83`) |
| R9 | Input validation: title and author required | ✓ implemented | `App.java:120-125` validate() checks null/blank; `BookApiTest.java:82-89` test confirms 400 |
| R10 | GET /health health-check endpoint | ✓ implemented | `App.java:41,52-54` returns `{"status":"ok"}`; `BookApiTest.java:60-65` test |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` (91 lines) — build, run, test, API docs, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `BookApiTest.java` has 6 @Test methods — all integration tests hitting real HTTP + SQLite |

## Build & Test

```text
Build/test scores read from retort.db (not re-run):
  test_coverage = 1.0  (build + all tests passed)
  code_quality  = 1.0  (lint clean)
  defect_rate   = 1.0  (build+test succeeded)
  idiomatic     = 0.7
  maintainability = 0.87
  token_efficiency = 0.018
```

```text
Tests (from BookApiTest.java — 6 JUnit 5 integration tests):
  1. healthEndpointReturnsOk          — GET /health → 200
  2. createBookReturns201AndAssignsId  — POST /books → 201
  3. createBookValidatesRequiredFields — POST /books empty → 400
  4. listBooksFiltersByAuthor          — GET /books?author=X → filtered
  5. getUpdateDeleteRoundTrip          — GET/PUT/DELETE → 200/200/204/404
  6. getReturns404ForUnknownId         — GET /books/99999999 → 404
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Java source only) | 444 |
| Lines of code (all tracked files) | 654 |
| Files (source + config) | 8 |
| Dependencies (Maven) | 5 |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0.0% |
| Build duration | stored score (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] No connection pooling — new JDBC connection per DAO operation (enhancement beyond spec)

## Reproduce

```bash
cd experiment-6/runs/language=java_model=claude-opus-4-7_tooling=none/rep1
mvn package
java -jar target/books-api.jar
mvn test
```
