# Evaluation: rest-api-crud · agent=codex effort=low language=go model=gpt-6.1-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** build+tests pass (test_coverage=0.71, defect_rate=1.0 from scores.json); 3 test functions / 0 skipped (3 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.9556 from scores.json
- **Architecture:** single-file `main.go` — `server` struct wraps `*sql.DB`; `routes()` returns an `http.ServeMux` (Go 1.22 method+path patterns) wrapped in a JSON-404 fallback. SQLite via `modernc.org/sqlite` (pure Go, no cgo).
- **Findings:** 0 items in `findings.jsonl` — clean run

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:106` `create` INSERTs all four fields, returns 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `main.go:124` `list` SELECTs all, returns JSON array |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.go:127` adds `WHERE author = ?` when param present; tested `main_test.go:80` |
| R4 | GET /books/{id} single book by id | ✓ implemented | `main.go:153` `get`, 404 on `sql.ErrNoRows` at `main.go:161` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:170` `update`, 404 when RowsAffected==0 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:196` `delete`, 204 on success, 404 when absent |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `main.go:15,29,35` `modernc.org/sqlite`, `CREATE TABLE books`; persistence verified `main_test.go:53` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `writeJSON`/`writeError` `main.go:68-75`; 201/200/204/400/404/503 used throughout |
| R9 | Validation: title and author required | ✓ implemented | `main.go:90-95` trims + rejects blank with 400; tested `main_test.go:88` |
| R10 | GET /health health-check endpoint | ✓ implemented | `main.go:45` pings DB, 200 `{"status":"ok"}` or 503 |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — build, run, env vars, curl examples, endpoint table |
| R12 | At least 3 unit/integration tests | ✓ implemented | 3 `func Test*` in `main_test.go:41,73,86`; 0 skips |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.71    # tests executed and passed (coverage fraction)
defect_rate   = 1.0     # build + tests succeeded
code_quality  = 0.9556
maintainability = 0.9420
idiomatic     = 0.80
```

```text
go test ./...   (3 tests, 0 skipped — from static grep, not re-run)
TestCRUDAndPersistence, TestListAndFilter, TestValidationAndHealth
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 233 (main.go) + 102 (main_test.go) = 335 |
| Files | 12 (incl. go.mod/go.sum/logs) |
| Dependencies | 43 (go.sum lines) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All 12 requirements implemented with test coverage; no skipped tests, no build/test failures, high code-quality score.

## Reproduce

```bash
cd "experiments/adrianco/experiment-92-terra61-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=go_model=gpt-6.1-terra_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" main_test.go                # 3 test functions
```
