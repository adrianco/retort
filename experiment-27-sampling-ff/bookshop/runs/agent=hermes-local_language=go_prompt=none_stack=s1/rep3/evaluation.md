# Evaluation: agent=hermes-local_language=go_prompt=none_stack=s1 · rep 3

## Summary

- **Factors:** language=go, agent=hermes-local (model Qwen3.6-35B-A3B), prompt=none, stack=s1, framework=gin
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass — from scores.json (`defect_rate=1.0`)
- **Lint:** pass — `code_quality=0.9556` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

Clean, spec-complete run. Every route in the pinned checklist is implemented, all handlers are exercised by passing tests, and the build/lint gates pass. Scores read from `scores.json` (inline gate) — no toolchain re-run.

## Requirements

Pinned checklist from `bookshop/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.go:71 createBookHandler`; `app_test.go:80 TestCreateBook` |
| R2 | GET /books lists all | ✓ implemented | `app.go:106 listBooksHandler`; `app_test.go:136 TestListBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:112-113` WHERE author=?; `app_test.go:183-196` filter assertion |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.go:142 getBookHandler`, `sql.ErrNoRows`→404; `TestGetBook`/`TestGetBookNotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.go:167 updateBookHandler`; `app_test.go:249 TestUpdateBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.go:234 deleteBookHandler`, rowsAffected→404; `TestDeleteBook`/`TestDeleteBookNotFound` |
| R7 | Data in SQLite / embedded | ✓ implemented | `app.go:9-10` go-sqlite3; `app.go:43 sql.Open("sqlite3", ...)` |
| R8 | JSON responses + status codes | ✓ implemented | `c.JSON(...)` throughout with 201/200/400/404/500 |
| R9 | Validation: title & author required | ✓ implemented | `app.go:24-25 binding:"required"` + `app.go:79` explicit check; `TestCreateBookValidation` |
| R10 | GET /health | ✓ implemented | `app.go:66 healthHandler`; `app_test.go:62 TestHealthEndpoint` |
| R11 | README with setup/run | ✓ implemented | `README.md` — prerequisites, `go mod tidy`, `go run app.go`, curl examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 11 `func Test*` in `app_test.go`; `test_coverage=0.582 (>0)` |

## Build & Test

Scores read from `scores.json` (skill Step 2 — no re-run):

```text
defect_rate      = 1.0     -> build + tests succeeded
test_coverage    = 0.582   -> tests executed; 58.2% statement coverage
code_quality     = 0.9556
maintainability  = 0.9256
idiomatic        = 0.62
token_efficiency = 0.0171
```

Agent stdout reports all 10 named tests passing; source contains 11 `Test*` functions (one extra, `TestListBooksEmpty`). No `t.Skip`/`t.Skipf` present.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 633 (app.go 280 + app_test.go 353) |
| Files (excl. `book-api` binary, .git) | 13 |
| Dependencies (go.sum lines) | 88 |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] PUT uses zero-value sentinels — `year=0` or clearing a string field is impossible (`app.go:196-211`)
2. [info] `main()` and file-backed `initDB` path uncovered (coverage 58.2%); tests use in-memory `:memory:` DB

No critical, high, or medium findings.

## Reproduce

```bash
cd "experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s1/rep3"
cat scores.json                      # build/test/lint scores (no re-run per skill Step 2)
grep -cE "^func Test" app_test.go     # test count
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count (0)
# Fallback verification only (not run here): go test -v ./...
```
