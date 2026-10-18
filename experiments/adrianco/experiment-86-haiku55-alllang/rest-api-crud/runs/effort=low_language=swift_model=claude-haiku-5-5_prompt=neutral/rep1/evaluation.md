# Evaluation: effort=low language=swift model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=swift, model=claude-haiku-5-5, effort=low, prompt=neutral (agent/framework unknown in stack.json)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective) — from `test_coverage=1.0`
- **Build:** pass (not re-run; `test_coverage=1.0` + `defect_rate=1.0` from scores.json ⇒ build + all tests passed)
- **Lint:** pass — `code_quality=0.8333` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores read from `scores.json` (inline gate; run not yet in retort.db). No build/test/lint re-run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `Routes.swift:21-35` → `BookStore.create`; `BookAPITests.swift:testCreateThenGetBook` |
| R2 | GET /books lists all books | ✓ implemented | `Routes.swift:37-42` → `BookStore.list`; `testListFiltersByAuthor` |
| R3 | GET /books ?author= filter | ✓ implemented | `BookStore.swift:51-58` (COLLATE NOCASE); `testListFiltersByAuthor`, `testAuthorFilterIsCaseInsensitive` |
| R4 | GET /books/{id} single, 404 if absent | ✓ implemented | `Routes.swift:44-52` returns 404 via `store.find`; `testCreateThenGetBook`, `testDeleteRemovesBook` |
| R5 | PUT /books/{id} updates | ✓ implemented | `Routes.swift:54-74` → `BookStore.update` (404 if absent); `testUpdateReplacesBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `Routes.swift:76-84` → `BookStore.delete` (404 if absent, 204 on success); `testDeleteRemovesBook` |
| R7 | SQLite / embedded DB storage | ✓ implemented | `BookStore.swift` uses sqlite3 via CSQLite shim; schema `BookStore.swift:22-30` |
| R8 | JSON responses + correct status codes | ✓ implemented | `jsonResponse`/`errorResponse` `Routes.swift:101-118`; 201/200/204/400/404 set throughout |
| R9 | Input validation: title & author required | ✓ implemented | `BookValidator.validate` `Book.swift:56-60`; `testCreateRejectsMissingTitleAndAuthor` |
| R10 | GET /health health check | ✓ implemented | `Routes.swift:17-19` returns `{"status":"ok"}`; `testHealthReturnsOK` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — build/test/run, env vars, endpoints, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 13 test functions across 2 files; `test_coverage=1.0` |

## Build & Test

Not re-run per skill Step 2 — stored mechanical scores stand in:

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.8333
             maintainability=0.8853  idiomatic=0.6  token_efficiency=0.0220
```

`test_coverage=1.0` ⇒ `swift build` + `swift test` succeeded and all tests passed.
Skip scan: `grep -rE "XCTSkip|XCTExpectFailure"` over Tests/ → 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 392 (Sources/*.swift) |
| Lines of code (tests) | 199 |
| Files | 8 |
| Dependencies | 1 (hummingbird) + CSQLite system lib |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All 3 findings are `info`-severity enhancements (no defects, no deductions):

1. [info] Validation exceeds spec — year range + ISBN-10/13 shape check (`Book.swift:53-102`)
2. [info] Case-insensitive author filter via COLLATE NOCASE (`BookStore.swift:54`)
3. [info] PUT is a full replace requiring all fields (`Routes.swift:64-69`) — valid REST interpretation

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=swift_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                               # stored mechanical scores (no re-run)
grep -rE "XCTSkip|XCTExpectFailure" Tests     # skip scan → none
grep -rE "func test" Tests --include="*.swift" | wc -l   # 13 tests
# full build/test (optional, slow): swift build && swift test
```
