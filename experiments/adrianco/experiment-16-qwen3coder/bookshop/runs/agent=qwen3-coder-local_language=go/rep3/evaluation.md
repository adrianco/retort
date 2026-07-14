# Evaluation: agent=qwen3-coder-local language=go · rep 3

## Summary

- **Factors:** language=go, agent=qwen3-coder-local, framework=unknown (stdlib net/http)
- **Status:** ok — builds and tests pass, but two real correctness bugs in update/delete and the create response
- **Requirements:** 11/12 implemented, 1 partial (R8), 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective) — but data-layer only; HTTP handlers untested
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint/Quality:** pass — code_quality=0.956, maintainability=0.985, idiomatic=0.72 (from scores.json)
- **Coverage:** test_coverage=0.325 (32.5%) from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 1 high, 2 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:168 handleCreateBook` + `CreateBook` persist all 4 fields (response id bug tracked under R8-post-id) |
| R2 | GET /books lists all | ✓ implemented | `main.go:195 handleGetAllBooks` / `GetAllBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:67` WHERE author=?; tested `TestBookStoreFilter` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `main.go:211 handleGetBook`; QueryRow returns sql.ErrNoRows → 404 (`main.go:215`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:228 handleUpdateBook` / `UpdateBook` (missing-id 404 path is dead — see R8) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:258 handleDeleteBook` / `DeleteBook` (missing-id 404 path is dead — see R8) |
| R7 | SQLite / embedded DB | ✓ implemented | `github.com/mattn/go-sqlite3`, `NewBookStore` opens `./books.db` (`main.go:27`) |
| R8 | JSON responses + appropriate status codes | ~ partial | PUT/DELETE return 200 not 404 for missing ids; POST response has `id:0`; DELETE returns plain text (`main.go:243-251,260-267,183-192,271-272`) |
| R9 | Validation: title & author required | ✓ implemented | `main.go:177` and `main.go:237` reject empty title/author with 400 |
| R10 | GET /health | ✓ implemented | `main.go:159` returns `{"status":"healthy"}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` documents `go mod tidy`, `go run main.go`, `go test -v`, endpoints |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 3 test funcs in `main_test.go`, run with coverage 0.325 > 0 |

## Build & Test

Build/test not re-run — scores read from `scores.json` (inline gate output):

```text
defect_rate     = 1.0    → build + tests succeeded
test_coverage   = 0.325  → tests executed; 32.5% coverage
code_quality    = 0.956
maintainability = 0.985
idiomatic       = 0.72
```

Tests present (all pass, none skipped):
```text
TestBookStoreFunctions   — create/get/getByID/update/delete on BookStore
TestBookStoreFilter      — ?author= filter returns matching rows
TestBookStoreEmptyFilter — empty store returns 0 books
```
All three call `BookStore` methods directly; no test exercises the HTTP handlers, validation, status codes, or `/health` — which is why the R8 bugs were not caught.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.go + main_test.go) | 430 (272 + 158) |
| Source files (excl. binary/db/logs) | 6 (main.go, main_test.go, go.mod, go.sum, README.md, TASK.md) |
| Dependencies (go.sum lines) | 2 (mattn/go-sqlite3) |
| Tests total | 3 |
| Tests effective (passed+failed) | 3 |
| Skip ratio | 0% |
| Coverage | 32.5% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [high] R8 — PUT/DELETE of a non-existent id return 200 OK instead of 404 (dead `sql.ErrNoRows` check; `Exec` never returns it and RowsAffected is unchecked).
2. [medium] POST /books returns `"id":0` — `CreateBook` discards `LastInsertId()`.
3. [medium] HTTP handlers/validation/health/status-codes untested (coverage 32.5%).
4. [low] DELETE returns plain-text body instead of JSON.
5. [low] Fragile not-found detection via `err.Error()` string comparison instead of `errors.Is`.

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop/runs/agent=qwen3-coder-local_language=go/rep3
cat scores.json                 # build/test/quality scores (do not re-run toolchain)
go vet ./... && go test -cover  # optional re-verification
```
