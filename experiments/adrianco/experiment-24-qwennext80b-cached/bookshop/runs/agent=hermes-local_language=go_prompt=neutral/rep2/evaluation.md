# Evaluation: agent=hermes-local language=go prompt=neutral · rep 2

## Summary

- **Factors:** language=go, agent=hermes-local, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — coverage 65.9%
- **Build:** pass (test_coverage=0.659 > 0 and defect_rate=1.0 from scores.json ⇒ build + tests succeeded)
- **Lint:** pass — code_quality=0.956, maintainability=0.959, idiomatic=0.70 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:161 createBook` INSERT with 4 fields |
| R2 | GET /books lists all books | ✓ implemented | `main.go:121 listBooks` SELECT all |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:128-129` WHERE author = ? |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.go:198 getBook`, 404 at `main.go:204` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:215 updateBook` UPDATE (see bug-1 on response body) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:256 deleteBook`, 204 at `main.go:275` |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:35` sql.Open("sqlite3","./books.db"), schema `main.go:60` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/404/400/405 across handlers; Content-Type set |
| R9 | Validation: title and author required | ✓ implemented | `main.go:169-176` (create), `main.go:223-230` (update) → 400 |
| R10 | GET /health health check | ✓ implemented | `main.go:73 healthHandler` returns {status:"ok"} |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` install/usage/API sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 15 `Test*` functions in `main_test.go`; coverage 0.659 |

## Build & Test

```text
# Not re-run — scores read from scores.json (retort's scorers already ran the toolchain)
test_coverage = 0.659   ⇒ build + tests executed and passed (coverage 65.9%)
defect_rate   = 1.0     ⇒ build+test succeeded
```

```text
15 Test* functions (TestHealthHandler, TestCreateBook, TestCreateBookMissingTitle/Author,
TestGetBook, TestGetBookNotFound, TestUpdateBook, TestUpdateBookNotFound, TestDeleteBook,
TestDeleteBookNotFound, TestListBooks, TestListBooksByAuthor, TestInvalidJSON,
TestInvalidBookID, TestMethodNotAllowed) + TestMain. 0 skips (grep t.Skip = 0).
Agent stdout: "The build succeeds and all 15 tests pass."
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 276 (main.go) + 322 (main_test.go) = 598 |
| Files (excl. binary + books.db) | ~5 tracked source/config (main.go, main_test.go, go.mod, go.sum, README.md) |
| Dependencies (go.sum lines) | 11 |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores cached) |

## Findings

Top findings (full list in `findings.jsonl`) — none at or above `medium`:

1. [low] README claims gorilla/mux but code uses stdlib net/http (`README.md:3` vs `go.mod:5`)
2. [low] PUT /books/{id} response echoes request body, not persisted row — id can be wrong if omitted (`main.go:253`)
3. [info] Health check does not verify DB connectivity (`main.go:73`)
4. [info] Very low token_efficiency=0.0059 for task size (scores.json)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-24-qwennext80b-cached/bookshop/runs/agent=hermes-local_language=go_prompt=neutral/rep2
cat scores.json          # cached mechanical scores (test_coverage, code_quality, ...)
grep -cE '^func Test' main_test.go   # test count (16 incl. TestMain)
grep -rE 't\.Skip\(' . --include='*.go' | wc -l   # skip count (0)
# To re-verify manually (not required — scores are cached):
# go test -v ./...
```
