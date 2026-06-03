# Evaluation: language=java_model=claude-opus-4-8_tooling=beads · rep 3

## Summary

- **Factors:** language=java, model=claude-opus-4-8, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 29 passed / 0 failed / 0 skipped (29 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** pass — code_quality=1.0 from retort.db
- **Architecture:** summary skill not invoked (standalone evaluation)
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `ApiServer.java:98` routes POST → `createBook`; `BookService.java:18` creates from body with all four fields; `BookRepository.java:49` persists to SQLite. Tests: `createReturns201AndAssignsId`, `createPersistsAndAssignsId` |
| R2 | GET /books lists all books | ✓ implemented | `ApiServer.java:95` routes GET → `listBooks`; `BookRepository.java:66` `findAll()` queries all. Test: `listReturnsAllBooks` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `ApiServer.java:135` extracts `author` query param; `BookRepository.java:68-70` adds `WHERE author = ?`. Tests: `listFiltersByAuthor` (integration + service) |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `ApiServer.java:120` routes GET with id → `getBook`; returns 404 if absent. Test: `getByIdReturnsBookOr404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `ApiServer.java:123` routes PUT → `updateBook`; `BookRepository.java:105` updates row; returns 404 if absent. Tests: `updateModifiesBookOr404`, `updateChangesExistingBook` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `ApiServer.java:126` routes DELETE → `deleteBook`; returns 204 on success, 404 if absent. Tests: `deleteRemovesBookOr404`, `deleteRemovesBook` |
| R7 | Data stored in SQLite | ✓ implemented | `BookRepository.java:28-35` uses JDBC `jdbc:sqlite:books.db`; `pom.xml` declares `sqlite-jdbc` dependency; schema auto-created via `CREATE TABLE IF NOT EXISTS books` |
| R8 | Returns JSON responses with appropriate HTTP status codes | ✓ implemented | `ApiServer.java:218-225` sets `Content-Type: application/json`; status codes: 201 (create), 200 (get/list/update), 204 (delete), 404 (not found), 400 (validation), 405 (method not allowed) |
| R9 | Input validation: title and author are required | ✓ implemented | `BookService.java:54-66` `requiredString()` throws `ValidationException` for null/blank title and author. Tests: `createWithoutTitleReturns400`, `createWithoutAuthorReturns400`, `missingTitleIsRejected`, `missingAuthorIsRejected`, `blankTitleIsRejected` |
| R10 | GET /health health-check endpoint | ✓ implemented | `ApiServer.java:33` registers `/health`; `handleHealth` (line 52) returns `{"status":"ok"}` with 200. Test: `healthCheckReturnsOk` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents build (`mvn test`), run (`java -jar target/book-api.jar`), env config, API reference |
| R12 | At least 3 unit/integration tests | ✓ implemented | 29 @Test methods across 3 test files: `BookApiIntegrationTest` (12), `BookServiceTest` (10), `JsonTest` (7). test_coverage=1.0 confirms all pass |

## Build & Test

```text
Stored scores from retort.db (build/test not re-run):
  test_coverage  = 1.0  (build + all tests passed)
  code_quality   = 1.0
  defect_rate    = 1.0
  idiomatic      = 0.88
  maintainability = 0.7352
  token_efficiency = 0.0483
```

```text
Test classes:
  BookApiIntegrationTest — 12 tests (end-to-end HTTP)
  BookServiceTest        — 10 tests (service + validation)
  JsonTest               —  7 tests (JSON parser/writer)
  Total: 29 passed, 0 failed, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 978 (main), 389 (test), 1367 total |
| Files | 24 |
| Dependencies | 2 (sqlite-jdbc, junit-jupiter) |
| Tests total | 29 |
| Tests effective | 29 |
| Skip ratio | 0.0% |
| Build duration | n/a (stored score used) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Custom JSON parser instead of library dependency — `Json.java` (344 lines) is hand-rolled; acceptable for minimal-dependency design

## Reproduce

```bash
cd experiment-6/runs/language=java_model=claude-opus-4-8_tooling=beads/rep3
cat stack.json
cat scores.json  # if present, otherwise query retort.db
# Scores were read from retort.db:
# sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'$.language')='java' AND json_extract(er.run_config_json,'$.model')='claude-opus-4-8' AND json_extract(er.run_config_json,'$.tooling')='beads' AND er.replicate=3 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1) AND rr.metric_name IN ('test_coverage','code_quality','defect_rate','maintainability','idiomatic','token_efficiency');"
grep -rE "@Disabled|@Ignore" src/test/ --include="*.java"
grep -c "@Test" src/test/java/com/example/books/*.java
find . -name "*.java" -not -path "*/target/*" | xargs wc -l
```
