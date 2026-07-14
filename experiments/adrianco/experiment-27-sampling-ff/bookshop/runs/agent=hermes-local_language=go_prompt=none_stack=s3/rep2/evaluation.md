# Evaluation: agent=hermes-local language=go prompt=none stack=s3 · rep 2

## Summary

- **Factors:** language=go, agent=hermes-local (model Qwen3.6-35B-A3B), prompt=none, stack=s3, framework=Gin
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective) — `defect_rate=1.0`, `test_coverage=0.584` (58.4% coverage) from scores.json
- **Build:** pass (defect_rate=1.0 ⇒ build + tests succeeded; not re-run)
- **Lint:** pass — `code_quality=0.956` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.go:70 createBookHandler` INSERT + 201; `app_test.go:85 TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `app.go:92 listBooksHandler`; `app_test.go:148 TestListBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:98-99` WHERE author=?; `app_test.go:177 TestListBooksByAuthor` |
| R4 | GET /books/{id} single book (404) | ✓ implemented | `app.go:128 getBookHandler` ErrNoRows→404; `app_test.go:207/234` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.go:149 updateBookHandler`; `app_test.go:250 TestUpdateBook` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.go:203 deleteBookHandler`; `app_test.go:286 TestDeleteBook` (verifies count=0) |
| R7 | Data stored in SQLite | ✓ implemented | `app.go:43` go-sqlite3, `CREATE TABLE books` |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/500 via `c.JSON` throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.go:24-25` binding:"required"; `app_test.go:128 TestCreateBookValidation` (400) |
| R10 | GET /health endpoint | ✓ implemented | `app.go:65 healthHandler` {"status":"ok"}; `app_test.go:63` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — prerequisites, `go mod tidy`, `go run app.go`, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 12 `func Test*` in `app_test.go`; test_coverage>0 |

## Build & Test

Not re-run (per skill — stored scores authoritative). From `scores.json`:

```text
test_coverage = 0.584   # 58.4% statement coverage, tests executed and passed
defect_rate   = 1.0     # build + all tests succeeded
code_quality  = 0.956
maintainability = 0.939
idiomatic     = 0.32
```

Agent stdout reports "All 12 tests pass, build succeeds cleanly." Tests run against an in-memory SQLite DB (`app_test.go:18 ":memory:"`), exercising the real handlers and DB layer.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 632 (app.go 258, app_test.go 374) |
| Files | 13 (incl. build/meta artifacts) |
| Dependencies (go.sum lines) | 88 |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] PUT partial-update cannot clear fields or set year to 0 — zero-value substitution in `app.go:173-188`.
2. [info] No pagination on GET /books (`app.go:92-125`) — not required by spec.
3. [info] On-disk `./books.db` created in cwd at startup (`app.go:43`) — tests correctly use `:memory:`.
4. [info] Low idiomatic score (0.32) despite high code_quality/maintainability — likely a scorer artifact, not a code defect.

## Reproduce

```bash
cd "experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s3/rep2"
cat scores.json                                   # stored mechanical scores (authoritative)
grep -cE "^func Test" app_test.go                 # 12 tests
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
# optional re-run: go test -v ./...
```
