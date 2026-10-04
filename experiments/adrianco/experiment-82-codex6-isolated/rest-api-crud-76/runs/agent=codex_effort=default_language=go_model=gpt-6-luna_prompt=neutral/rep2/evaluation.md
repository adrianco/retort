# Evaluation: agent=codex effort=default language=go model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from scores.json (defect_rate=1.0)
- **Lint:** pass — code_quality=0.956 (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Scores read from `scores.json` (inline gate output; DB not re-queried): `test_coverage=0.589`, `defect_rate=1.0`, `code_quality=0.956`, `maintainability=0.900`, `idiomatic=0.8`, `token_efficiency=0.020`. `test_coverage=0.589` is a coverage fraction (>0), and `defect_rate=1.0` confirms the build compiled and all tests passed — no re-run performed.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:89-105` createBook INSERTs 4 fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:107-135` listBooks SELECTs all, ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:110-113` appends `WHERE author = ?`; test at `main_test.go:56` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.go:137-148` getBook, `sql.ErrNoRows`→404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:150-171` updateBook, RowsAffected==0→404 (full-replace; see low-1) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:173-189` deleteBook, 204 on success, 404 if absent |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:15,242` modernc.org/sqlite; real DB file, not in-memory state |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `writeJSON`/`writeError` `main.go:224-231`; 201/200/204/404/400/405/500 used |
| R9 | Validation: title & author required | ✓ implemented | `main.go:204-209` trims and rejects empty title/author with 400; test `main_test.go:40` |
| R10 | GET /health endpoint | ✓ implemented | `main.go:45-56` /health pings DB, returns `{"status":"ok"}`; test `main_test.go:93` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — run, env vars, endpoints, test |
| R12 | ≥3 unit/integration tests | ✓ implemented | 3 `TestXxx` functions in `main_test.go`; test_coverage=0.589 (>0) |

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: test_coverage=0.589  defect_rate=1.0  code_quality=0.956
=> build compiled, `go test` ran, all tests passed, statement coverage 58.9%
```

```text
go test ./...   (would run 3 tests: TestCreateValidateAndFilterBooks,
                 TestGetUpdateDeleteBook, TestHealthAndNotFound)
0 skips detected (grep t.Skip/t.Skipf == 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 357 (main.go 258 + main_test.go 99) |
| Files | 12 (incl. go.mod/go.sum, README, logs, meta) |
| Dependencies | 1 direct (modernc.org/sqlite); go.sum 50 lines |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] PUT is full-replace, not partial update — `main.go:150-171` (acceptable for R5)
2. [info] Strict, hardened request decoding beyond spec — `main.go:191-215`
3. [info] Health check verifies DB connectivity (503 when down) — `main.go:50-54`

No critical, high, or medium findings. All 12 pinned requirements are implemented with test coverage; the run is a clean pass.

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=go_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json                                   # stored mechanical scores (no re-run)
grep -rEc "t\.Skip\(|t\.Skipf\(" . --include="*.go"   # skip count == 0
grep -rE "^func Test" *.go                         # 3 test functions
# optional full verification:
go test ./...
```
