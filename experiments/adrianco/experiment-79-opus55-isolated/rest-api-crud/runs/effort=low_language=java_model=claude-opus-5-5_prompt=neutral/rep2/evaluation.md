# Evaluation: rest-api-crud effort=low language=java model=claude-opus-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=java, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — from `test_coverage=1.0` in `scores.json` (build ran and all tests passed)
- **Lint:** pass — `code_quality=1.0` in `scores.json`, 0 warnings
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `BookServer.java:97` → `BookRepository.create` (`BookRepository.java:36`); test `BookApiTest.createThenGetBook:64` |
| R2 | GET /books lists all books | ✓ implemented | `BookServer.java:96` → `repo.list`; test `listReturnsAllBooksAndFiltersByAuthor:116` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookRepository.java:49-52` `WHERE author = ? COLLATE NOCASE`; test `BookApiTest.java:125-131` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `BookServer.java:107` `found(repo.find(id))`; tests `createThenGetBook:72`, `unknownBookAndBadIdsAndRoutes:171` |
| R5 | PUT /books/{id} updates | ✓ implemented | `BookServer.java:108` → `repo.update`; test `updateReplacesBook:135` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `BookServer.java:109-113`; test `deleteRemovesBook:158` |
| R7 | Data stored in SQLite | ✓ implemented | `BookRepository.java:22-33` `jdbc:sqlite:`; test `dataPersistsAcrossReopen:13` (survives reopen) |
| R8 | JSON responses + status codes | ✓ implemented | `send()` sets `application/json` (`BookServer.java:241-248`); 201/200/204/400/404/405 across routes |
| R9 | Validation: title & author required | ✓ implemented | `parseBook`/`requiredText` (`BookServer.java:197-239`); test `createRejectsMissingTitleAndAuthor:91` |
| R10 | GET /health | ✓ implemented | `BookServer.java:90-93` pings DB; test `healthReturnsOk:56` |
| R11 | README with setup/run | ✓ implemented | `README.md` (build, run, config, API, examples) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 13 `@Test` methods across 2 files; `test_coverage=1.0` |

No requirements partial or missing.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per evaluate-run step 2).

```text
scores.json: {"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.824, "idiomatic": 0.76,
              "token_efficiency": 0.069}
```

`test_coverage=1.0` ⇒ `mvn package` built the project and all 13 JUnit tests passed.
`code_quality=1.0` ⇒ no lint/quality warnings. Skip scan (`@Disabled`/`assumeTrue`/`@Ignore`)
found 0 in both test files.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main, source only) | 399 |
| Lines of code (test) | 214 |
| Files (src/) | 6 |
| Dependencies (pom `<dependency>`) | 4 |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build | pass (from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; both are info-level enhancements beyond spec:

1. [info] Beyond-spec HTTP correctness: 405+Allow header, Location header on create, 1 MiB body cap (413)
2. [info] Case-insensitive author filter via `COLLATE NOCASE`

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=java_model=claude-opus-5-5_prompt=neutral/rep2"
cat scores.json                                    # mechanical scores (build/test/lint)
grep -rEc "@Disabled|assumeTrue|@Ignore" src/test  # skip scan → 0
grep -rE "@Test" src/test | wc -l                  # 13 tests
# Full build+test (only if re-verifying; scores.json already has results):
# mvn -q package
```
