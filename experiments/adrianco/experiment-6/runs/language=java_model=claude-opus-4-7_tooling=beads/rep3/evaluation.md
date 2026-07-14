# Evaluation: language=java_model=claude-opus-4-7_tooling=beads · rep 3

## Summary

- **Factors:** language=java, model=claude-opus-4-7, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** pass — code_quality=1.0 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|-----|-----|----|
| R1 | POST /books creates a new book | ✓ implemented | `BookController.java:16` create(), `BookRepository.java:43` SQL INSERT, tested `BookApiIntegrationTest.java:70` |
| R2 | GET /books lists all books | ✓ implemented | `BookController.java:27` list(), `BookRepository.java:63` findAll(), tested `BookApiIntegrationTest.java:97` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookController.java:28` queryParam("author"), `BookRepository.java:65` WHERE clause, tested `BookApiIntegrationTest.java:109` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `BookController.java:32` get(), `BookRepository.java:85` findById(), tested `BookApiIntegrationTest.java:79,157` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookController.java:40` update(), `BookRepository.java:98` UPDATE SQL, tested `BookApiIntegrationTest.java:120` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookController.java:54` delete(), `BookRepository.java:115` DELETE SQL, tested `BookApiIntegrationTest.java:140` |
| R7 | Data stored in SQLite | ✓ implemented | `BookRepository.java:16` jdbc:sqlite URL, `pom.xml:33` sqlite-jdbc dependency |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | All controller methods use `ctx.json()` with correct codes: 201, 200, 404, 400, 204 |
| R9 | Input validation: title and author required | ✓ implemented | `BookController.java:88-93` validate(), tested `BookApiIntegrationTest.java:88` returns 400 |
| R10 | GET /health health-check endpoint | ✓ implemented | `BookController.java:64` health(), `App.java:17` route, tested `BookApiIntegrationTest.java:59` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents Build, Run, Test sections with Maven commands |
| R12 | At least 3 unit/integration tests | ✓ implemented | 7 @Test methods in `BookApiIntegrationTest.java` (exceeds minimum) |

## Build & Test

```text
Build/test scores read from retort.db (not re-run):
  test_coverage  = 1.0   (build + all tests passed)
  code_quality   = 1.0   (lint clean)
  defect_rate    = 1.0   (build+test succeeded)
  idiomatic      = 0.87
  maintainability = 0.92
  token_efficiency = 0.008
```

```text
Test suite: BookApiIntegrationTest (JUnit 5 integration tests)
  healthEndpointReturnsUp         — PASS
  createBookAndFetchById          — PASS
  createBookValidatesRequiredFields — PASS
  listAndFilterByAuthor           — PASS
  updateBookReplacesFields        — PASS
  deleteBookReturns204AndThen404  — PASS
  getMissingBookReturns404        — PASS
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 484 (Java) |
| Files | 14 |
| Dependencies | 5 (javalin, jackson-databind, sqlite-jdbc, slf4j-simple, junit-jupiter) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | from retort.db scores |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Tests exceed minimum requirement (7 vs 3)

## Reproduce

```bash
cd experiment-6/runs/language=java_model=claude-opus-4-7_tooling=beads/rep3
cat stack.json
cat TASK.md
# Scores were read from retort.db, not re-run
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='java' AND json_extract(er.run_config_json,'\$.model')='claude-opus-4-7' AND json_extract(er.run_config_json,'\$.tooling')='beads' AND er.replicate=3 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1) AND rr.metric_name IN ('test_coverage','code_quality','defect_rate','maintainability','idiomatic','token_efficiency');"
find src -name "*.java" | xargs wc -l
grep -c "@Test" src/test/java/com/example/bookapi/BookApiIntegrationTest.java
grep -rE "@Disabled|@Ignore" src --include="*.java" | wc -l
```
