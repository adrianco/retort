# Evaluation: agent=hermes-local · language=go · model=Qwen3-Coder-Next-4bit · stack=m80 · rep 2

## Summary

- **Factors:** language=go, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json); build+test gate succeeded
- **Lint:** pass — `code_quality=0.956` (scores.json); 0 blocking warnings, 2 low-severity style notes
- **Architecture:** run-summary skill unavailable in this session — single-package Go/Gin service (`app.go`) with an httptest-based test suite (`app_test.go`)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

Scores read from `scores.json` (inline gate): `test_coverage=0.648` (64.8% Go coverage), `defect_rate=1.0`, `code_quality=0.956`, `maintainability=0.922`, `idiomatic=0.57`, `token_efficiency=0.017`. The DB row was not present (inline-scored run) so `scores.json` is authoritative.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.go:157 createBook` INSERTs all four fields; `TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `app.go:99 listBooks` all-books branch; `TestListBooks`/`TestEmptyDatabase` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:105-125` author branch `WHERE author = ?`; `TestListBooks` filter case |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.go:200 getBook`, `sql.ErrNoRows`→404; `TestGetBook` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.go:228 updateBook`; `TestUpdateBook` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.go:283 deleteBook`, 204; `TestDeleteBook` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `app.go:48 sql.Open("sqlite3", ...)`, `go-sqlite3`, `createTable` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `c.JSON` throughout; 201/200/404/400/204/500 used |
| R9 | Validation: title and author required | ✓ implemented | `binding:"required,min=1"` + explicit `TrimSpace` checks `app.go:166-173,255-262`; `TestCreateBook`/`TestTitleValidationOnUpdate` |
| R10 | GET /health health check | ✓ implemented | `app.go:94 healthCheck` returns `{"status":"ok"}`; `TestHealthCheck` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — install, run, build, curl examples, testing |
| R12 | At least 3 unit/integration tests | ✓ implemented | 9 test functions in `app_test.go`; `test_coverage=0.648 > 0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` per skill policy.

```text
defect_rate = 1.0        # build + test gate passed
test_coverage = 0.648    # 64.8% Go statement coverage (coverage.out present, mode: set)
```

Agent stdout reports all 9 tests passing (TestHealthCheck, TestCreateBook, TestListBooks,
TestGetBook, TestUpdateBook, TestDeleteBook, TestInvalidBookID, TestEmptyDatabase,
TestTitleValidationOnUpdate). Skip scan: 0 `t.Skip`/`t.Skipf`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.go) | 315 |
| Lines of code (app_test.go) | 390 |
| Files (excl. .git) | 14 |
| Dependencies (go.sum lines) | 91 |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build/test gate | pass (defect_rate=1.0) |

## Findings

Top items (full list in `findings.jsonl`) — none at high or above:

1. [low] Q1 — Dead error-handling branch in `listBooks` from `err` shadowing (`app.go:103,149`)
2. [low] Q2 — Test id-building `string(rune('0'+bookID))` only correct for single-digit IDs (`app_test.go:189`)
3. [info] Q3 — POST/PUT responses omit `created`/`updated` and re-marshal a partial object (`app.go:190,273`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop/runs/agent=hermes-local_language=go_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep2"
cat scores.json                                  # mechanical scores (inline gate)
grep -rEc "t\.Skip\(|t\.Skipf\(" . --include="*.go"   # skip scan (0)
grep -rEo "^func Test[A-Za-z0-9]+" *.go          # enumerate tests
# tests already gated: defect_rate=1.0, coverage.out present
```
