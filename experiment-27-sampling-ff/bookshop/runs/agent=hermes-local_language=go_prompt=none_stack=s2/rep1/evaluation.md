# Evaluation: hermes-local · go · stack=s2 · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local, prompt=none, stack=s2
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 functions / 13 subtests, 0 failed, 0 skipped (all effective) — `defect_rate=1.0`, `test_coverage=0.611` (61.1% coverage) from scores.json
- **Build:** pass — from scores.json (`defect_rate=1.0`; not re-run)
- **Lint:** pass — `code_quality=0.9556` from scores.json (3 minor code-smell findings noted below)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.go:98 createBook` INSERTs all four fields, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.go:135 listBooks` selects all rows |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:141-142` filters on `author` query param; `TestListBooks` "filter by author" |
| R4 | GET /books/{id} single book | ✓ implemented | `app.go:171 getBook`, 404 on `sql.ErrNoRows` (app.go:183) |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.go:196 updateBook` with pointer-based partial update |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.go:271 deleteBook`, 404 when 0 rows affected |
| R7 | SQLite / embedded DB | ✓ implemented | `app.go:44` `sql.Open("sqlite3", "./books.db")`, go-sqlite3 dep |
| R8 | JSON + appropriate status codes | ✓ implemented | `c.JSON` with 201/200/400/404/500 throughout handlers |
| R9 | Validate title & author required | ✓ implemented | `app.go:77 validateBook`; `TestCreateBook` missing-title/author cases |
| R10 | GET /health | ✓ implemented | `app.go:91 healthCheck` returns `{status:ok}` |
| R11 | README with setup/run | ✓ implemented | `README.md` documents `go mod tidy`, `go run app.go`, API examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 7 test funcs / 13 subtests, `test_coverage=0.611 > 0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill Step 2):

```text
scores.json: defect_rate=1.0  → build + tests passed
             test_coverage=0.611 → 61.1% statement coverage, tests executed
             code_quality=0.9556, maintainability=0.9374, idiomatic=0.42
```

Agent's own log (`_agent_stdout.log`) reports all 7 suites / 18 sub-tests passing. Skip scan (`grep t.Skip`) found 0 skipped/disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, app.go) | 320 |
| Lines of code (tests, app_test.go) | 569 |
| Files (excl. .git) | 13 |
| Dependencies (go.sum entries) | 91 |
| Tests total (funcs/subtests) | 7 / 13 |
| Tests effective | 13 (0 skipped) |
| Skip ratio | 0% |
| Coverage | 61.1% |

## Findings

Full list in `findings.jsonl`:

1. [medium] isbn `NOT NULL UNIQUE` not validated — duplicate/omitted isbn returns opaque 500 (`app.go:55` vs `validateBook` app.go:77)
2. [low] `scanBook` is dead code (`app.go:67`, never called)
3. [low] Unreachable `fmt.Println` after blocking `r.Run` (`app.go:318-319`)

No critical, high, or requirement findings — a clean, spec-complete run.

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s2/rep1
cat scores.json                                   # mechanical scores (build/test/lint)
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count = 0
go test -v ./...                                  # optional re-verification
```
