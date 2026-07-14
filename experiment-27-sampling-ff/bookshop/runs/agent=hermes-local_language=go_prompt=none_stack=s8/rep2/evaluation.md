# Evaluation: agent=hermes-local_language=go_prompt=none_stack=s8 · rep 2

## Summary

- **Factors:** language=go, agent=hermes-local (model Qwen3.6-35B-A3B), framework=gin, prompt=none, stack=s8
- **Status:** ok — builds and all tests pass (defect_rate=1.0), but the test suite exercises a duplicated copy of the handlers, not the shipped code (test_coverage=0.03)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list `REQUIREMENTS.json`)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — from `defect_rate=1.0` / `test_coverage=0.03` in `scores.json` (not re-run)
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Architecture:** run-summary skill unavailable (not registered); summarized inline below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 1 high, 0 medium, 1 low)

## Requirements

Pinned checklist from `bookshop/REQUIREMENTS.json` (constant denominator, 12 items).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.go:82` POST handler INSERTs, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.go:104-137` list handler |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:110-114` `WHERE author = ?` branch |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.go:139-159`, `sql.ErrNoRows`→404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.go:161-194` UPDATE, 404 if no rows |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.go:196-216` DELETE, 404 if no rows |
| R7 | Data stored in SQLite | ✓ implemented | `app.go:43` `sql.Open("sqlite3","./books.db")`, go-sqlite3 driver |
| R8 | JSON + correct status codes | ✓ implemented | `c.JSON` with 201/200/400/404/500 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.go:24-25` `binding:"required"`; `TestCreateBookMissingFields`→400 |
| R10 | GET /health | ✓ implemented | `app.go:78-80` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md:19-35` setup, run, test instructions |
| R12 | ≥3 unit/integration tests | ✓ implemented | 10 tests in `app_test.go`, all run & pass (test_coverage=0.03 > 0) |

R12 meets its pinned bar (≥3 tests that run), but see the high finding: the tests
validate a re-declared copy of the routes, so the *shipped* handlers are untested.

## Build & Test

Not re-run — scores read from `scores.json` (per skill step 2):

```text
defect_rate     = 1.0     -> build + test suite executed and passed
test_coverage   = 0.03    -> line coverage of app.go is ~3%
code_quality    = 0.9556  -> lint/quality
maintainability = 0.7675
idiomatic       = 0.68
token_efficiency= 0.0239
```

The 1.0-vs-0.03 split is explained by test structure: `app_test.go:16-178`
`setupTestRouter` rebuilds every route inline against an in-memory DB. `main()`
and `initDB()` in `app.go` are never called, so the production handlers register
zero coverage even though 10 behavioral tests pass. Agent stdout confirms all 10
green (`TestHealthCheck` … `TestDeleteBookNotFound`).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go source) | 657 (app.go 220, app_test.go 437) |
| Files (excl .git) | 13 |
| Direct dependencies | 2 (gin-gonic/gin, mattn/go-sqlite3) |
| Tests total | 10 (+ TestMain harness) |
| Tests effective | 10 |
| Skip ratio | 0% |
| API calls / tokens | 17 calls, 444k total tokens |

## Architecture

`run-summary` skill was unavailable (not a registered skill). Inline summary:
single-package `main` Go service. `app.go` holds the `Book`/`CreateBookRequest`/
`UpdateBookRequest` models, a package-level `*sql.DB`, `initDB()` (opens file
SQLite + `CREATE TABLE IF NOT EXISTS`), a `scanRow` helper, and `main()` which
wires six Gin routes plus `/health` and serves on `:8080`. Parameterized queries
throughout (no SQL-injection exposure). `app_test.go` mirrors the route wiring in
`setupTestRouter` against an in-memory DB — the source of the coverage gap.

## Findings

Full list in `findings.jsonl`:

1. [high] Tests re-declare all handlers instead of exercising `app.go` — production routes have ~3% coverage (`app_test.go:16-178`)
2. [low] PUT /books/{id} full-replace with no validation can blank required title/author (`app.go:31-36`, `174-177`)

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s8/rep2
cat scores.json                       # build/test/lint scores (not re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" app_test.go     # 11 (incl. TestMain)
# to actually run: go mod tidy && go test -cover ./...
```
