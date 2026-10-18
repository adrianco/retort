# Evaluation: effort=low language=java model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=claude-haiku-5-5, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + all tests passed)
- **Lint:** pass (code_quality=1.0 from scores.json) — 0 warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (fixed denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `BookServer.java:107 createBook` → `BookRepository.java:40 create`, returns 201; test `BookApiTest.java:48 createThenGetBook` |
| R2 | GET /books lists all | ✓ implemented | `BookServer.java:101 listBooks` → `findAll(null)`; test `BookApiTest.java:68` asserts all 3 returned |
| R3 | GET /books ?author= filter | ✓ implemented | `BookRepository.java:66 findAll` WHERE author COLLATE NOCASE; test `BookApiTest.java:71` asserts 2 |
| R4 | GET /books/{id} single + 404 | ✓ implemented | `BookServer.java:116 getBook`, 404 when empty; test `BookApiTest.java:108` (999 → 404) |
| R5 | PUT /books/{id} updates | ✓ implemented | `BookServer.java:125 updateBook` → `BookRepository.java:87 update`, 200/404; test `BookApiTest.java:83` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BookServer.java:138 deleteBook` → `delete`, 204/404; test `BookApiTest.java:88-90` |
| R7 | Data stored in SQLite | ✓ implemented | `pom.xml:20 sqlite-jdbc`; `BookRepository.java:27 jdbc:sqlite` + CREATE TABLE |
| R8 | JSON responses + status codes | ✓ implemented | `BookServer.java:198 sendJson` (Jackson); 201/200/204/400/404/405/500 across handlers |
| R9 | Validation: title + author required | ✓ implemented | `BookInput.java:29-33 validate` → 400; test `BookApiTest.java:94 rejectsInvalidInput` |
| R10 | GET /health health-check | ✓ implemented | `BookServer.java:56 handleHealth` returns `{status}` 200/503; test `BookApiTest.java:113` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build, run, env vars, endpoints, examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 6 `@Test` in `BookApiTest.java`; test_coverage=1.0 |

No `prompt`-factor requirements (prompt=neutral is a style directive, not an additional spec file).

## Build & Test

Not re-run — stored mechanical scores from `scores.json` stand in (per skill step 2):

```text
scores.json: test_coverage=1.0, code_quality=1.0, defect_rate=1.0,
             maintainability=0.706, idiomatic=0.70, token_efficiency=0.030
```

`test_coverage=1.0` ⇒ `mvn test` compiled and all 6 tests passed. `code_quality=1.0` ⇒ no lint warnings. The tests are real integration tests: each spins up a `BookServer` on an ephemeral port against a temp-dir SQLite DB and drives it over HTTP (`BookApiTest.java:32-45`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 565 (434 main / 131 test) |
| Files (excl. build artifacts) | 15 |
| Dependencies | 3 (sqlite-jdbc, jackson-databind, junit-jupiter) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores from archive) |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; both are informational enhancements beyond spec:

1. [info] Validation goes beyond spec (year 1400–2100 range + ISBN format) — `BookInput.java:35-40`
2. [info] Extra error handling (405 / 400 non-numeric id / 500 db error) — `BookServer.java:76,87,97`

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=java_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores (build+test+lint)
cat ../../REQUIREMENTS.json                        # pinned 12-requirement checklist
grep -rE "@Disabled|assumeTrue|@Ignore" src        # skip detection → 0
grep -rc "@Test" src/test/java/com/example/books/BookApiTest.java   # 6
# To actually build/test (not required for scoring): mvn test
```
