# Evaluation: language=java_model=opus_tooling=beads · rep 1

## Summary

- **Factors:** language=java, model=opus, tooling=beads
- **Status:** ok (note: main source files missing from archive — scored from retort.db + test evidence)
- **Requirements:** 11/12 implemented, 1 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** pass — code_quality=1.0 from retort.db
- **Architecture:** Javalin REST API with SQLite backend (source files missing from archive; summary skill unavailable)
- **Findings:** 3 items in `findings.jsonl` (1 critical, 0 high, 1 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✓ implemented | `BookApiTest.java:67-75` — POST with title/author/year/isbn → 201; test_coverage=1.0 |
| R2 | GET /books lists all books | ✓ implemented | `BookApiTest.java:92-96` — GET /books → 200, size≥2; test_coverage=1.0 |
| R3 | GET /books ?author= filter | ✓ implemented | `BookApiTest.java:97-101` — GET /books?author=Asimov → 1 result matching; test_coverage=1.0 |
| R4 | GET /books/{id} returns single book | ✓ implemented | `BookApiTest.java:85-89` — GET by id → 200; `BookApiTest.java:113` → 404 after delete; test_coverage=1.0 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `BookApiTest.java:104-108` — PUT → 200, body contains updated title; test_coverage=1.0 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `BookApiTest.java:110-114` — DELETE → 204, subsequent GET → 404; test_coverage=1.0 |
| R7 | SQLite embedded DB | ✓ implemented | `BookApiTest.java:32` jdbc:sqlite: URI; `pom.xml:28` sqlite-jdbc 3.46.1.0 dependency |
| R8 | JSON responses + proper HTTP status codes | ✓ implemented | Tests verify 200, 201, 204, 400, 404; JSON parsed via ObjectMapper; test_coverage=1.0 |
| R9 | Input validation: title and author required | ~ partial | `BookApiTest.java:79` tests missing title → 400; no test for missing author; source unavailable to verify |
| R10 | GET /health endpoint | ✓ implemented | `BookApiTest.java:60-64` — GET /health → 200, body contains "ok"; test_coverage=1.0 |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — 42 lines covering Build, Run, Endpoints, Test sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `BookApiTest.java` — 6 test methods (health, createBook, createValidationFails, getById, listAndFilter, updateAndDelete) |

## Build & Test

```text
Stored scores from retort.db (build/test NOT re-run per skill policy):
  test_coverage   = 1.0   (build + all tests passed)
  code_quality    = 1.0
  defect_rate     = 1.0
  idiomatic       = 0.68
  maintainability = 0.93
  token_efficiency = 0.50
```

```text
Test methods (from BookApiTest.java):
  6 @Test methods, 0 @Disabled/@Ignore, 0 skipped
  Tests: health, createBook, createValidationFails, getById, listAndFilter, updateAndDelete
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (visible in archive) | 116 (test only; main source missing) |
| Files (total in workspace) | 9 (excl. evaluation artifacts) |
| Source files (visible) | 1 (BookApiTest.java) |
| Dependencies (Maven) | 5 (javalin, jackson-databind, sqlite-jdbc, slf4j-simple, junit-jupiter) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. **[critical]** Main application source files missing from archive — App.java, BookDao.java not present; code review and rebuild impossible
2. **[medium]** R9: Author-required validation not tested — only title validation confirmed by tests; source unavailable to verify author check
3. **[info]** Enhancement: 6 test methods (double the 3-minimum requirement)

## Reproduce

```bash
cd experiment-1/runs/language=java_model=opus_tooling=beads/rep1
# Source files missing from archive — cannot rebuild
# Scores from retort.db: test_coverage=1.0, code_quality=1.0, defect_rate=1.0
# To verify test structure:
grep -c "@Test" src/test/java/com/example/BookApiTest.java
# To query stored scores:
sqlite3 -readonly ../../retort.db "SELECT metric_name, value FROM run_results WHERE run_id = (SELECT id FROM experiment_runs WHERE json_extract(run_config_json,'$.language')='java' AND json_extract(run_config_json,'$.model')='opus' AND json_extract(run_config_json,'$.tooling')='beads' AND replicate=1 AND status='completed' ORDER BY finished_at DESC LIMIT 1);"
```
