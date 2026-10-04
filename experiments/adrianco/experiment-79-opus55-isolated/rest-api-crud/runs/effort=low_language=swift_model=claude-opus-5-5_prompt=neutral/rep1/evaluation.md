# Evaluation: rest-api-crud (effort=low, language=swift, model=claude-opus-5-5, prompt=neutral) · rep 1

## Summary

- **Factors:** language=swift, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective) — from `test_coverage=1.0` in `scores.json`
- **Build:** pass — not re-run (test_coverage=1.0 in scores.json ⇒ build + all tests passed)
- **Lint:** pass — `code_quality=0.83` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `Router.swift:37`→`BookStore.swift:37 create`; `Book.swift:50 BookInput.parse` accepts all 4 fields |
| R2 | GET /books lists all books | ✓ implemented | `Router.swift:34`→`BookStore.swift:46 list`; test `testListAndAuthorFilter:79` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `Router.swift:35` reads `author` query item; `BookStore.swift:50` `WHERE author = ? COLLATE NOCASE`; test `:83` |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `Router.swift:50`→`BookStore.swift:58 get`; 404 at `Router.swift:51`; test `:118,:123` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `Router.swift:53`→`BookStore.swift:68 update`; full-resource replace; test `testUpdateBook:97` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `Router.swift:57`→`BookStore.swift:80 delete`; 204/404; test `testDeleteBook:112` |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `BookStore.swift` uses SQLite3 C API; persistence test `:137 testDataPersistsAcrossReopen` |
| R8 | JSON responses with appropriate HTTP codes | ✓ implemented | `HTTP.swift:29 json`, `:38 error`; 200/201/204/400/404/405/413/500 used throughout Router |
| R9 | Input validation: title & author required | ✓ implemented | `Book.swift:58 requiredString` rejects missing/empty/non-string → 400; test `testCreateValidation:57` |
| R10 | GET /health endpoint | ✓ implemented | `Router.swift:28` returns `200 {status:ok}`; test `testHealth:26` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Requirements, Run, env vars, endpoints sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 13 test functions across 4 XCTestCase classes; `test_coverage=1.0` |

No requirements are missing or partial. No enhancements introduce deductions.

## Build & Test

Build and tests were **not re-run** per the evaluate-run skill — the mechanical
scores were already computed during `retort run` and stored in `scores.json`:

```text
scores.json: test_coverage=1.0, defect_rate=1.0, code_quality=0.833,
             maintainability=0.860, idiomatic=0.78, token_efficiency=0.098
```

`test_coverage=1.0` ⇒ `swift build` + `swift test` succeeded and all tests passed.
No skip/ignore/xfail markers found in `Tests/` (grep returned none).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Swift, source + tests) | 726 |
| Files (excl. build artifacts) | 17 |
| Dependencies | 0 third-party (system sqlite3 + Network.framework) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level enhancements, no deductions:

1. [info] SQL-injection regression test beyond spec (`BookAPITests.swift:90`)
2. [info] End-to-end tests over a real socket (`BookAPITests.swift:169`)
3. [info] Persistence verified across DB reopen (`BookAPITests.swift:137`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=swift_model=claude-opus-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores (build+test)
grep -rEn "XCTSkip|skip|xfail" Tests/             # skip detection (none)
grep -rEc "func test" Tests/                       # 13 tests
# To rebuild from scratch (optional, not required for eval):
swift test
```
