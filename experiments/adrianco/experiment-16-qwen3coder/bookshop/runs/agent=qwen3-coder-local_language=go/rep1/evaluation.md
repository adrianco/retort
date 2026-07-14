# Evaluation: agent=qwen3-coder-local language=go · rep 1

## Summary

- **Factors:** language=go, agent=qwen3-coder-local, framework=unknown (stdlib `net/http`)
- **Status:** ok — builds and tests pass; two correctness gaps on missing-ID update/delete
- **Requirements:** 9/11 implemented, 2 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — `test_coverage=0.452`
- **Build:** pass (from `defect_rate=1.0` in scores.json)
- **Lint:** pass — `code_quality=0.9556` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 2 high, 1 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create (title, author, year, isbn) | ✓ implemented | `main.go:129 handleCreateBook` / `CreateBook`; test `Create Book` |
| R2 | GET /books list with `?author=` filter | ✓ implemented | `main.go:160 handleGetBooks`, `GetBooks` LIKE filter; tests `Get All Books`, `Get Books by Author` |
| R3 | GET /books/{id} | ✓ implemented | `main.go:358 handleGetBookWithID` / `176 handleGetBook`; test `Get Book by ID` |
| R4 | PUT /books/{id} update | ~ partial | works for existing IDs (test `Update Book`) but returns 200 for missing IDs — `main.go:106` |
| R5 | DELETE /books/{id} | ~ partial | works for existing IDs (test `Delete Book`) but returns 200 for missing IDs — `main.go:112` |
| R6 | Store data in SQLite | ✓ implemented | `main.go:29 sql.Open("sqlite3", ...)`, `mattn/go-sqlite3` |
| R7 | JSON responses with appropriate status codes | ✓ implemented | `respondWithJSON` used throughout; 201/400/404/405/500 (caveat: R4/R5 wrong 200) |
| R8 | Input validation (title & author required) | ✓ implemented | `main.go:142-149`; test `Create Book Validation` |
| R9 | Health check GET /health | ✓ implemented | `main.go:285 handleHealthCheck`; test `Health Check` |
| R10 | README with setup & run instructions | ✓ implemented | `README.md` — setup, run, test, curl examples |
| R11 | At least 3 unit/integration tests | ✓ implemented | `main_test.go` — 8 subtests |

## Build & Test

```text
go build ./...    # pass — defect_rate=1.0 (scores.json)
go test ./...     # 8 subtests pass, 0 skipped — test_coverage=0.452 (scores.json)
```

Coverage is 45.2% because the router-wired `handle*WithID` handlers are never
exercised by tests (the tests call the standalone `handle*` variants instead) —
see finding `dup-handlers`. Scores read from `scores.json`; toolchain not re-run.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.go + main_test.go) | 677 (413 + 264) |
| Source files | 10 (incl. README, go.mod/go.sum, summary/) |
| Dependencies | 1 direct (`mattn/go-sqlite3`) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| test_coverage | 0.452 |
| code_quality | 0.9556 |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [high] R4 — PUT /books/{id} returns 200 for a non-existent book (dead `sql.ErrNoRows` branch; `db.Exec` never returns it)
2. [high] R5 — DELETE /books/{id} returns 200 for a non-existent book (same root cause)
3. [medium] dup-handlers — production `/books/{id}` handlers are untested duplicates of the tested standalone handlers (drives the 45.2% coverage)
4. [low] put-response-body — PUT returns a status message instead of the updated Book resource

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-16-qwen3coder/bookshop/runs/agent=qwen3-coder-local_language=go/rep1
cat scores.json                 # mechanical scores (build/test/lint) — not re-run
go build ./... && go test -v    # optional re-verification
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
```
