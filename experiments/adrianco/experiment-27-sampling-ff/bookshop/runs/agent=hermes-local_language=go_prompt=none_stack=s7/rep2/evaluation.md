# Evaluation: agent=hermes-local_language=go_prompt=none_stack=s7 · rep 2

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown, prompt=none, stack=s7
- **Status:** ok — all requirements implemented; build + tests pass
- **Requirements:** 11/11 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json); not re-run
- **Lint:** pass — `code_quality=0.956` (scores.json); `idiomatic=0.42`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 1 info)

Mechanical scores read from `scores.json` (inline gate output) — not re-run per skill guidance:
`test_coverage=0.263`, `defect_rate=1.0`, `code_quality=0.956`, `maintainability=0.882`,
`idiomatic=0.42`, `token_efficiency=0.018`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create (title, author, year, isbn) | ✓ implemented | `app.go:231` handler → `CreateBook` `app.go:89`; `TestCreateBook` |
| R2 | GET /books list + `?author=` filter | ✓ implemented | `app.go:270` → `GetAllBooks` LIKE filter `app.go:113`; `TestGetAllBooks` |
| R3 | GET /books/{id} single book | ✓ implemented | `app.go:292` → `GetBook` `app.go:152`; `TestGetBookByID`/`TestGetBookNotFound` |
| R4 | PUT /books/{id} update | ✓ implemented | `app.go:314` → `UpdateBook` `app.go:167`; `TestUpdateBook` (partial-update semantics, see put-sentinel-1) |
| R5 | DELETE /books/{id} | ✓ implemented | `app.go:370` → `DeleteBook` `app.go:196`; `TestDeleteBook`/`TestDeleteBookNotFound` |
| R6 | Store data in SQLite | ✓ implemented | go-sqlite3 driver, WAL mode `app.go:47-56`; schema `app.go:70-81` |
| R7 | JSON responses + appropriate HTTP status codes | ✓ implemented | `c.JSON` with 201/200/400/404/500 throughout `app.go:223-391` |
| R8 | Input validation (title & author required) | ✓ implemented | `binding:"required"` `app.go:26-27` + trim/non-empty checks `app.go:241-256` |
| R9 | GET /health health check | ✓ implemented | `app.go:223`; `TestHealthCheck` |
| R10 | README with setup + run instructions | ✓ implemented | `README.md` — prerequisites, `go mod tidy`, `go run app.go`, curl examples |
| R11 | At least 3 unit/integration tests | ✓ implemented | 11 `Test*` functions in `app_test.go` |

Caveat: R1–R9 are verified against the tests' **duplicate** router (`newTestRouter`,
`app_test.go:60`), not `main()`'s router — see finding test-arch-1.

## Build & Test

Not re-run — mechanical scores taken from `scores.json` per evaluate-run Step 2.

```text
defect_rate = 1.0        # build + test suite succeeded
test_coverage = 0.263    # tests executed; low coverage — main()'s handlers untested
```

Skip scan (`grep t.Skip`): 0 skipped tests → 11 effective of 11.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.go) | 396 |
| Lines of code (app_test.go) | 494 |
| Files (excl. .git) | 17 (incl. compiled binary + test DB) |
| Dependencies (go.sum lines) | 88 |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Coverage (from scores.json) | 26.3% |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] Production `main()` HTTP handlers untested — test suite reimplements the routes in `newTestRouter()` (`app_test.go:60`); coverage 26.3%.
2. [low] ~180 lines of handler logic duplicated between `app.go` and `app_test.go`; idiomatic score 0.42.
3. [low] PUT uses zero-value sentinels (`app.go:341-356`) — cannot set year=0/clear a field, and skips required-field validation.
4. [info] Compiled `book-api` binary + `test_books.db*` left in workspace.

## Reproduce

```bash
cd "experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s7/rep2"
cat scores.json                                   # mechanical scores (not re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skipped tests → 0
grep -cE "^func Test" app_test.go                 # test count → 11
# Optional full verification:
go test -v -cover ./...
```
