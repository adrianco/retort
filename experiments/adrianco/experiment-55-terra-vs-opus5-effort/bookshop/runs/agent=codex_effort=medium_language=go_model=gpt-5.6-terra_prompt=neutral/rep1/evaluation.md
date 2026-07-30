# Evaluation: agent=codex effort=medium language=go model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=go, agent=codex, model=gpt-5.6-terra, effort=medium, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from stored scores (`defect_rate=1.0`)
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Architecture:** single-file `net/http` service (`run-summary` skill unavailable in this environment)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores are read from `scores.json` (inline gate output) — the skill forbids re-running
the toolchain. `defect_rate=1.0` ⇒ build + all tests passed; `test_coverage=0.617` is
Go's statement-coverage fraction (tests executed successfully, confirmed by
`defect_rate=1.0`). This is a clean, fully-conforming run.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:47,64-75` INSERT persists all 4 fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.go:76-103` SELECT all, returns `[]Book` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:77-82` adds `WHERE author = ?` when set |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.go:114-124` + `find` returns 404 on `sql.ErrNoRows` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:125-141` UPDATE, 404 when RowsAffected=0 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:142-153` DELETE, 204/404 |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `main.go:16,193` `modernc.org/sqlite`; table created `main.go:31-39` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `writeJSON`/`writeError` `main.go:178-186`; 201/200/204/400/404/500 used |
| R9 | Validation: title and author required | ✓ implemented | `decodeBook` `main.go:170-174` returns 400 when either blank |
| R10 | GET /health health-check | ✓ implemented | `main.go:45,54-60` pings DB, returns `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — run, endpoints, env vars, test |
| R12 | At least 3 unit/integration tests | ✓ implemented | `main_test.go` — 3 `Test*` funcs covering CRUD, filter, validation, health |

## Build & Test

Not re-run (per skill). Stored scores from `scores.json`:

```text
defect_rate       = 1.0     (build + tests succeeded)
test_coverage     = 0.617   (Go statement coverage; tests executed)
code_quality      = 0.9556
maintainability   = 0.9547
idiomatic         = 0.70
token_efficiency  = 0.0180
```

Tests (`main_test.go`) exercise via `httptest`: create+get, author-filter+update,
validation+delete+health. Each uses an in-memory shared-cache SQLite DB per test.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.go) | 209 |
| Lines of code (main_test.go) | 98 |
| Files (source) | 2 (main.go, main_test.go) + README, go.mod, go.sum |
| Dependencies (go.sum lines) | 41 (modernc.org/sqlite + transitive) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build/test | pass (defect_rate=1.0) |

## Findings

All findings are info-level enhancements; no requirement gaps or defects.

1. [info] Request body hardening beyond spec — `MaxBytesReader` + `DisallowUnknownFields` (`main.go:164-165`)
2. [info] Server `ReadHeaderTimeout` set (`main.go:206`)
3. [info] `?author=` filter is exact-match only — satisfies R3 (`main.go:79-82`)

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=medium_language=go_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json          # stored build/test/quality scores (do not re-run toolchain)
grep -cE '^func Test' main_test.go   # 3 tests
go test ./... -cover     # optional local re-verify: build + tests + coverage
```
