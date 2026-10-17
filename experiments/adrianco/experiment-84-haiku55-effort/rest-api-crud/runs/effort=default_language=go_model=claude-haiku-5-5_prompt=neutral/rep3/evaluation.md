# Evaluation: effort=default_language=go_model=claude-haiku-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 test functions passed / 0 failed / 0 skipped (9 effective)
- **Build:** pass (defect_rate=1.0 from retort.db)
- **Lint:** pass — code_quality=1.0 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.go:48 handleCreate` → `store.go:61 Create` |
| R2 | GET /books lists all books | ✓ implemented | `server.go:62 handleList` → `store.go:93 List` |
| R3 | GET /books ?author= filter | ✓ implemented | `server.go:63` reads `author` query → `store.go:96` WHERE author COLLATE NOCASE; tested `server_test.go:144` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `server.go:71 handleGet`; `store.go:82` ErrNotFound → 404 `server.go:156` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.go:84 handleUpdate` → `store.go:123 Update` (404 when n==0) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.go:101 handleDelete` → `store.go:142 Delete` (204/404) |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:9` modernc.org/sqlite, `store.go:12` schema, file-backed |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `server.go:181 writeJSON` sets Content-Type; 201/200/204/400/404/409/503 across handlers |
| R9 | Input validation: title and author required | ✓ implemented | `book.go:52-57` Validate; tested `server_test.go:160 TestCreateValidation` |
| R10 | GET /health health-check | ✓ implemented | `server.go:37 handleHealth` pings DB, returns `{"status":"ok"}`; tested `server_test.go:233` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Setup (`go mod download`), Run (`go run .`), flags, endpoints |
| R12 | At least 3 unit/integration tests | ✓ implemented | 9 test functions across `book_test.go` + `server_test.go`; test_coverage=0.755 (>0) |

No partial, missing, or cannot-verify items. No prompt-factor (`neutral`) added checkable instructions beyond TASK.md.

## Build & Test

Build/test were not re-run — stored scores from `retort.db` are authoritative:

```text
defect_rate      = 1.0     # build + tests succeeded
test_coverage    = 0.755   # coverage fraction (> 0 ⇒ tests executed and passed)
code_quality     = 1.0
requirement_coverage = 1.0
idiomatic        = 0.92
maintainability  = 0.8737
```

9 test functions, 0 `t.Skip`/`t.Skipf` calls → 9 effective tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 514 |
| Lines of code (tests) | 314 |
| Files | 17 (incl. logs/meta/go.sum) |
| Dependencies (go.sum lines) | 50 |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Run duration | 668s (whole run, from retort.db) |
| Tokens / cost | 6.82M / $0.57 |

## Findings

Top 5 by severity (full list in `findings.jsonl`) — all info-level enhancements, no deductions:

1. [info] ISBN normalization + ISBN-10/13 format validation beyond spec (`book.go:72,88`)
2. [info] Duplicate-ISBN uniqueness enforced with 409 Conflict (`store.go:21,158`)
3. [info] Request hardening: body-size cap, unknown-field + trailing-content rejection (`server.go:116,118,131`)
4. [info] Graceful shutdown on SIGINT/SIGTERM (`main.go:32,47`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=default_language=go_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json            # stored mechanical scores (build/test/lint not re-run)
grep -rnE "^func Test" *.go # 9 test functions
grep -rcE "t\.Skip" *.go    # 0 skips
# cross-check retort.db (read-only):
sqlite3 -readonly ../../../retort.db "SELECT metric_name,value FROM run_results WHERE run_id=(SELECT id FROM experiment_runs WHERE json_extract(run_config_json,'\$.model')='claude-haiku-5-5' AND replicate=3 AND status='completed' ORDER BY finished_at DESC LIMIT 1);"
```
