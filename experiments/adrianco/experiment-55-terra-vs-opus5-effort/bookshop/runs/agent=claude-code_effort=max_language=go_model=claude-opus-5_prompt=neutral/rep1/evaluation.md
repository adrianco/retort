# Evaluation: agent=claude-code effort=max language=go model=claude-opus-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-opus-5, agent=claude-code, effort=max, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 29 test functions, all passing / 0 failed / 0 skipped (29 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=1.0`, `idiomatic=0.87` (scores.json)
- **Architecture:** stdlib `net/http` (Go 1.22 method-aware ServeMux), SQLite via pure-Go `modernc.org/sqlite`; layered `main` → `Server` (handlers/middleware) → `Store` (DB) → `Book`/`BookInput` (model+validation). `run-summary` skill unavailable — not generated.
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.go:81 handleCreate` → `store.go:113 Create`; 201 + Location header |
| R2 | GET /books lists all books | ✓ implemented | `server.go:98 handleList` → `store.go:158 List`; empty → `[]` |
| R3 | GET /books ?author= filter | ✓ implemented | `server.go:99` reads `author`; `store.go:161` `WHERE author = ? COLLATE NOCASE`; test `TestListBooks`/`TestStoreListFiltersByAuthorCaseInsensitively` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `server.go:109 handleGet` → `store.go:144 Get`; `ErrNotFound`→404 (`server.go:284`) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.go:124 handleUpdate` → `store.go:191 Update` (full-replace PUT semantics, tx) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.go:144 handleDelete` → `store.go:228 Delete`; 204, 404 if absent |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:12` `modernc.org/sqlite`; schema `store.go:29`; WAL/busy_timeout pragmas |
| R8 | JSON responses w/ appropriate status codes | ✓ implemented | `server.go:299 writeJSON`; 201/200/204/400/404/409/415/500 across handlers |
| R9 | Input validation: title & author required | ✓ implemented | `book.go:73 Validate` (`title is required`/`author is required`)→400; `TestCreateBookValidation` |
| R10 | GET /health | ✓ implemented | `server.go:69 handleHealth` pings DB; 200 ok / 503 unavailable; `TestHealthEndpoint` |
| R11 | README.md with setup & run instructions | ✓ implemented | `README.md` — Setup/run, endpoint reference, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 29 Test functions; `test_coverage=0.878`, `defect_rate=1.0` |

No requirement gaps. Enhancements beyond spec: 409 duplicate-ISBN handling, ISBN format validation, panic-recovery + structured-logging middleware, graceful shutdown, request body-size cap, 405 with `Allow` header.

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
code_quality      = 1.0
idiomatic         = 0.87
test_coverage     = 0.878   (build + all tests passed; value is coverage %)
defect_rate       = 1.0     (build + test succeeded)
maintainability   = 0.806
token_efficiency  = 0.0143
```

Skipped-test scan (`grep -rE "t\.Skip\(|t\.Skipf\("`): 0 matches → 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, *.go incl. tests) | 2311 |
| Source files (*.go) | 8 (4 impl + 4 test) |
| Dependencies (direct) | 1 (`modernc.org/sqlite`) |
| Tests total | 29 |
| Tests effective | 29 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`), all info-level — clean run:

1. [info] Duplicate-ISBN → 409 conflict handling (beyond spec)
2. [info] Panic recovery, structured logging, graceful shutdown, body-size cap (beyond spec)
3. [info] 29 tests, far exceeding the 3-test minimum, covering concurrency & persistence-across-reopen

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=claude-code_effort=max_language=go_model=claude-opus-5_prompt=neutral/rep1"
cat scores.json                                   # stored build/test/lint scores
grep -rhE "^func Test" *_test.go | wc -l          # test count = 29
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skips = 0
go test ./...                                     # optional: re-verify (defect_rate=1.0)
```
