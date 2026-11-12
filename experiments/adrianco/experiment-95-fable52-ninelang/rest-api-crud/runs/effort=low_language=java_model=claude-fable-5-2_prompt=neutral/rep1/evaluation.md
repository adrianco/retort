# Evaluation: rest-api-crud · effort=low language=java model=claude-fable-5-2 prompt=neutral · rep 1

## Summary

- **Factors:** language=java, model=claude-fable-5-2, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass — from `test_coverage=1.0` (build + all tests ran; not re-run per skill §2)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** `run-summary` skill not available in this session; see inline notes below.
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `App.java:44` + `BookRepository.create` `:38`; test `createAndGetBook` `AppTest.java:66` |
| R2 | GET /books lists all | ✓ implemented | `App.java:46` + `BookRepository.list` `:52`; test `listAndFilterByAuthor` `:106` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookRepository.java:54` `WHERE author = ? COLLATE NOCASE`; test `:115` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `App.java:48` `find(id).orElseThrow(notFound)`; test `unknownAndInvalidIds` `:149` |
| R5 | PUT /books/{id} updates | ✓ implemented | `App.java:53` + `BookRepository.update` `:81`; test `updateBook` `:122` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `App.java:59` + `BookRepository.delete` `:94`; test `deleteBook` `:140` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `BookRepository.java:19` `jdbc:sqlite:`; test `dataPersistsAcrossRestart` `:159` proves non-memory |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `ctx.json(...)` throughout; 201/200/204/400/404 set explicitly; `App.java:67-85` error mapping |
| R9 | Validation: title and author required | ✓ implemented | `App.java:114-115,143-155` `requiredText`; test `validationRejectsMissingTitleAndAuthor` `:91` |
| R10 | GET /health | ✓ implemented | `App.java:42` returns `{"status":"ok"}`; test `healthCheck` `:57` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build, run, config, API table, curl examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 9 `@Test` methods in `AppTest.java`; `test_coverage=1.0` |

## Build & Test

Not re-run (skill §2 — stored mechanical scores stand in):

```text
scores.json: {"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.880, "idiomatic": 0.8, "token_efficiency": 0.0425}
```

`test_coverage=1.0` ⇒ `mvn test` built the project and all tests passed. No skipped/disabled
tests found (`grep -E "@Disabled|assumeTrue|@Ignore|\.skip"` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main, source only) | 279 |
| Lines of code (test) | 166 |
| Files (excl. target/.git) | 14 |
| Dependencies (`<dependency>` in pom.xml) | 5 |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Maintainability | 0.880 |
| Idiomatic | 0.80 |

## Findings

All 4 findings are info-level (enhancements/notes); no deductions:

1. [info] JSON error bodies for all error paths, including unmatched routes (exceeds spec)
2. [info] ?author= filter is case-insensitive exact match (documented)
3. [info] Test verifies SQLite persistence survives a restart (strong R7 evidence)
4. [info] PUT full-replacement semantics documented in README

## Reproduce

```bash
cd experiments/adrianco/experiment-95-fable52-ninelang/rest-api-crud/runs/effort=low_language=java_model=claude-fable-5-2_prompt=neutral/rep1
cat scores.json                                    # mechanical scores (not re-run)
grep -rc "@Test" src/test                          # test count
grep -rnE "@Disabled|assumeTrue|@Ignore|\.skip" src # skip detection -> 0
# full verification: mvn test   (not run here; test_coverage=1.0 already recorded)
```
