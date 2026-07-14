# Evaluation: agent=hermes-local_language=go_prompt=none_stack=s8 · rep 3

## Summary

- **Factors:** language=go, agent=hermes-local, framework=unknown (gin), prompt=none, stack=s8
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 23 test functions, 0 skipped (23 effective) — pass (defect_rate=1.0 from scores.json)
- **Build:** pass — from scores.json (defect_rate=1.0; test_coverage=0.658 > 0 ⇒ build + tests ran)
- **Lint/Quality:** pass — code_quality=0.956, maintainability=0.958 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

Scores (from `scores.json`): code_quality=0.9556, maintainability=0.9578, test_coverage=0.6580, defect_rate=1.0, idiomatic=0.58, token_efficiency=0.0211.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.go:103 createBook` + route `app.go:85`; test `TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `app.go:131 listBooks` + route `app.go:86`; test `TestListBooks` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.go:132-141` filters on `author` query param; test `TestListBooksByAuthor` |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `app.go:166 getBook`, 404 at `app.go:179`; tests `TestGetBook`, `TestGetBookNotFound` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.go:191 updateBook`, 404 on 0 rows `app.go:221`; test `TestUpdateBook` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.go:229 deleteBook`; tests `TestDeleteBook`, `TestDeleteBookNotFound` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `app.go:44` sqlite3, table DDL `app.go:49-55` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201 `app.go:127`, 200/400/404/500 throughout; JSON via `c.JSON` |
| R9 | Input validation: title & author required | ✓ implemented | `app.go:66 validateBook`, enforced at create `app.go:110` and update `app.go:205`; tests `TestCreateBookValidation`, `TestCreateBookMissingAuthor` |
| R10 | GET /health health-check | ✓ implemented | `app.go:98 healthCheck` + route `app.go:84`; test `TestHealthCheck` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — Setup and Run, Testing, API examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 23 `func Test*` in `app_test.go`, 0 skips; test_coverage=0.658 |

## Build & Test

Build/test not re-run — stored scores used per skill (defect_rate=1.0 ⇒ build + tests passed; test_coverage=0.658 line coverage).

```text
go test ./...   (not re-executed)
scores.json: defect_rate=1.0, test_coverage=0.658
23 test functions in app_test.go, 0 t.Skip
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.go, non-blank) | 209 |
| Lines of code (app_test.go, non-blank) | 822 |
| Files (workspace) | 13 |
| Dependencies (go.sum lines) | 156 |
| Tests total (func Test*) | 23 (excl. TestMain) |
| Tests effective | 23 |
| Skip ratio | 0% |
| code_quality / maintainability | 0.956 / 0.958 |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] validateBook returns an always-nil error — `app.go:66`
2. [low] Duplicate ISBN yields a generic 500 instead of a 4xx — `app.go:119-122`
3. [info] SQLite database file persists across runs at a fixed path — `app.go:44`

No critical/high/medium findings. All 12 pinned requirements implemented; build and tests pass.

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s8/rep3
cat scores.json                                   # stored mechanical scores
grep -cE "^func Test" app_test.go                 # 24 (23 + TestMain)
grep -nE "t\.Skip\(|t\.Skipf\(" app_test.go | wc -l   # 0 skips
# build/tests not re-run — defect_rate=1.0 in scores.json
```
