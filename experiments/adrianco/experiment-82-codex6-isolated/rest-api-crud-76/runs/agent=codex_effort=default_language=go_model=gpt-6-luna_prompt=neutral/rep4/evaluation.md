# Evaluation: agent=codex effort=default language=go model=gpt-6-luna prompt=neutral · rep 4

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from scores.json (`defect_rate=1.0`, `test_coverage=0.587`; not re-run)
- **Lint:** pass — `code_quality=0.956` from scores.json
- **Architecture:** single-file Go service (`main.go`), stdlib `net/http` router + SQLite via `mattn/go-sqlite3`; `run-summary` not separately invoked (single-file codebase described inline)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:90-106` createBook INSERTs all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:108-136` listBooks, returns JSON array |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.go:111-113` filters `WHERE author = ?` |
| R4 | GET /books/{id} returns one book | ✓ implemented | `main.go:138-149` getBook; 404 on `sql.ErrNoRows` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:151-172` updateBook; 404 when RowsAffected=0 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:174-186` deleteBook; 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:14,31-37,241` go-sqlite3, CREATE TABLE books |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/204/400/404/405 via `writeJSON`/`writeError` (`main.go:223-234`) |
| R9 | Validation: title and author required | ✓ implemented | `main.go:214-222` validateBook → 400 |
| R10 | GET /health health check | ✓ implemented | `main.go:45-52` returns `{"status":"ok"}` 200 |
| R11 | README with setup + run instructions | ✓ implemented | `README.md:1-35` requirements, run, endpoints, test |
| R12 | At least 3 unit/integration tests | ✓ implemented | `main_test.go` 3 Test funcs; `test_coverage=0.587 > 0` |

## Build & Test

Not re-run — stored scores used per skill Step 2.

```text
scores.json
defect_rate     = 1.0    (build + tests succeeded)
test_coverage   = 0.587  (tests executed; ~58.7% coverage)
code_quality    = 0.956
maintainability = 0.897
idiomatic       = 0.77
token_efficiency= 0.0346
```

```text
go test ./...  (not re-run; 3 tests, 0 skips)
TestCreateAndGetBook
TestListFiltersAuthorAndValidation
TestUpdateDeleteNotFoundAndHealth
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 350 (main.go 256 + main_test.go 94) |
| Files | 12 (incl. archive/meta) |
| Dependencies | 1 (mattn/go-sqlite3) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — no defects; all info-level:

1. [info] Hardened JSON decoding beyond spec (DisallowUnknownFields, 1MB cap, trailing-data rejection)
2. [info] Configurable listen address and DB path via env vars
3. [info] Coverage ~58.7%; invalid-id/invalid-JSON/method-not-allowed branches untested

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=go_model=gpt-6-luna_prompt=neutral/rep4"
cat scores.json                                   # stored build/test/lint scores
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -rE "^func Test" . --include="*.go"          # 3 tests
```
