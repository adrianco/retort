# Evaluation: agent=hermes-local language=go prompt=none stack=s5 · rep 2

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown (Gin), prompt=none, stack=s5
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective) — from defect_rate=1.0
- **Build:** pass — from retort.db/scores.json (defect_rate=1.0; not re-run)
- **Lint:** pass — code_quality=0.9556 (idiomatic=0.45)
- **Coverage:** test_coverage=0.569 (56.9%)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

Pinned checklist from `bookshop/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.go:79 createBook`, INSERT at `app.go:102`, tested `app_test.go:80` |
| R2 | GET /books lists all books | ✓ implemented | `app.go:132 listBooks`, tested `app_test.go:157` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:133-156` WHERE author=?, tested `app_test.go:186` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.go:186 getBook`, 404 at `app.go:201`, tested `app_test.go:219` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.go:217 updateBook`, tested `app_test.go:265` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.go:295 deleteBook`, tested `app_test.go:315` |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `app.go:41 initDB` opens sqlite3, file `books.db` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201/200/400/404/500 via `c.JSON` throughout |
| R9 | Validation: title and author required | ✓ implemented | `binding:"required"` `app.go:25-26` + checks `app.go:88-100`, tested `app_test.go:128,365` |
| R10 | GET /health health check | ✓ implemented | `app.go:72 healthCheck`, tested `app_test.go:57` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — endpoints, setup, run, test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 10 tests in `app_test.go`, test_coverage=0.569 (>0) |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate) per skill policy.

```text
scores.json: defect_rate=1.0  ⇒ build + tests succeeded
             test_coverage=0.569 (56.9% coverage)
             code_quality=0.9556, maintainability=0.9014, idiomatic=0.45
```

```text
go test — 10 test functions, 0 skips (grep t.Skip == 0)
TestHealthCheck, TestCreateBook, TestCreateBookMissingTitle, TestListBooks,
TestGetBook, TestUpdateBook, TestDeleteBook, TestCreateBookMissingAuthor,
TestCreateBookEmptyBody, TestListBooksEmpty
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.go + app_test.go) | 804 (362 + 442) |
| Source files (go/md, excl. logs/artifacts) | 5 |
| Direct dependencies | 2 (gin-gonic/gin, mattn/go-sqlite3) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Coverage | 56.9% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Update cannot clear a field or set year to 0 — `app.go:253-271`
2. [low] Hard-coded SQLite filename and package-global db handle — `app.go:39,42`
3. [info] Error-path test coverage exceeds the 3-test minimum — `app_test.go`
4. [info] Low idiomatic score (0.45) despite high code quality — `scores.json`, `app.go:190`

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s5/rep2
cat scores.json                                   # mechanical scores (do not re-run toolchain)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" app_test.go                 # 10 tests
# optional live check: go test -v ./...
```
