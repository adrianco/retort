# Evaluation: rest-api-crud · agent=codex effort=low language=swift model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=swift, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — `test_coverage=1.0` from scores.json
- **Build:** pass — not re-run (stored `test_coverage=1.0` ⇒ build + all tests passed)
- **Lint:** pass — `code_quality=0.8333` from scores.json
- **Architecture:** `BookService` (SQLite-backed service + request router) + `BookServer` (hand-rolled HTTP/1.1 socket server) + `CSQLite` system-library shim
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `BookService.swift` `("POST", true)` → INSERT, returns 201 + book |
| R2 | GET /books lists all books | ✓ implemented | `BookService.swift` `("GET", true)` → `SELECT ... ORDER BY id` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookService.swift` queryItems `author` → `WHERE author = ?`; tested `testFilterAndValidation` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `("GET", false)` → `WHERE id = ?`, else 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `("PUT", false)` → UPDATE; 404 when `sqlite3_changes==0` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `("DELETE", false)` → DELETE; 404 if no rows changed |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `CSQLite` system lib; `CREATE TABLE books ...`; persistence tested `testPersistenceAndErrors` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `json()` encoder; 201/200/400/404/405/500 branches; server maps reason phrases |
| R9 | Validation: title and author required | ✓ implemented | trims whitespace, rejects empty → 400; tested (blank title, `{}`) |
| R10 | GET /health endpoint | ✓ implemented | `path == "/health"` → `{"status":"ok"}` 200; tested |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — build/test/run, env vars, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 3 `func test*` in `BookServiceTests.swift`, 0 skips |

## Build & Test

Build/test not re-run per skill Step 2 — stored mechanical scores stand in:

```text
scores.json: {"test_coverage": 1.0, "code_quality": 0.8333, "defect_rate": 0.9237,
              "maintainability": 0.7090, "idiomatic": 0.3, "token_efficiency": 0.0206}
```

`test_coverage=1.0` ⇒ `swift build` + `swift test` succeeded and all 3 tests passed. Skip grep over `Tests/` found 0 skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 257 (BookService 119, BookServer 94, Tests 44) |
| Files (excl. .cache/.git) | 15 |
| Dependencies | 0 SwiftPM packages (CSQLite system lib only) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

No correctness or coverage defects. Full list in `findings.jsonl` (2 info):

1. [info] Zero-dependency implementation — raw BSD socket HTTP server + CSQLite, with Content-Length handling, Transfer-Encoding rejection, and 1MiB body cap.
2. [info] Author filter is exact/case-sensitive match (documented in README; spec-compliant).

## Reproduce

```bash
cd "experiments/adrianco/experiment-92-terra61-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=swift_model=gpt-6.1-terra_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores (build/test/lint)
grep -rnE "XCTSkip|t\.Skip|#\[ignore\]" Tests/    # skipped-test scan (0)
swift build && swift test                         # optional: re-verify (scores already show pass)
```
