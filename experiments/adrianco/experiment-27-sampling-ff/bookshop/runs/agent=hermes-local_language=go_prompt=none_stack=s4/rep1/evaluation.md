# Evaluation: agent=hermes-local_language=go_prompt=none_stack=s4 · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown, prompt=none, stack=s4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — `test_coverage=0.586`, `defect_rate=1.0` from `scores.json` (build compiled to 16MB `book-api` binary)
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.go:73 createBookHandler`; `TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `app.go:115 listBooksHandler`; `TestListBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:116-125`; `TestListBooks` asserts 2 for Author X |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.go:150 getBookHandler`; `TestGetBook`/`TestGetBookNotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.go:175 updateBookHandler`; `TestUpdateBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.go:240 deleteBookHandler`; `TestDeleteBook` |
| R7 | Data stored in SQLite | ✓ implemented | `app.go:43 sql.Open("sqlite3", ...)`, `initDB` table create |
| R8 | JSON responses + correct status codes | ✓ implemented | 201/200/404/400 throughout; `c.JSON` on every path |
| R9 | Validation: title & author required | ✓ implemented | `app.go:81-88` + `binding:"required"`; `TestCreateBookMissing*` |
| R10 | GET /health | ✓ implemented | `app.go:66 healthHandler`; `TestHealthEndpoint` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — prerequisites, setup, run, examples |
| R12 | >= 3 unit/integration tests | ✓ implemented | 13 `Test*` funcs, `test_coverage=0.586` > 0 |

## Build & Test

Scores read from `scores.json` (no re-run per evaluate-run skill):

```text
test_coverage = 0.586   # build compiled + all tests pass (0 => tests didn't run)
defect_rate   = 1.0      # build + test succeeded
code_quality  = 0.9556
maintainability = 0.9173
idiomatic     = 0.48
token_efficiency = 0.0222
```

```text
go test -v   (from _agent_stdout.log)
TestHealthEndpoint..TestCreateBookEmptyBody — 13/13 PASS, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 673 (app.go 289 + app_test.go 384) |
| Files (excl. .git) | 14 (incl. 16MB `book-api` binary + build DBs) |
| Dependencies (direct) | 2 (gin-gonic/gin, mattn/go-sqlite3) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] PUT cannot set year=0 or clear optional string fields — `app.go:212-219`
2. [info] Create/Update responses rebuild JSON manually instead of returning the Book struct — `app.go:105-111,230-236`
3. [info] No uniqueness constraint on isbn — `app.go:48-55`
4. [info] Error/500 branches uncovered (test_coverage=0.586) — `scores.json`

No critical/high/medium findings — this is a clean, spec-conformant run.

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s4/rep1
cat scores.json                       # stored build/test/lint scores (do not re-run)
grep -cE "^func Test" app_test.go      # 13 tests
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
# optional fresh run: CGO_ENABLED=1 go test -v
```
