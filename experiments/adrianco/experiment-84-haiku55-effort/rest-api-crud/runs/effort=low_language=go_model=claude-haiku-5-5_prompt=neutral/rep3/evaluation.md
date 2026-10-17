# Evaluation: effort=low language=go model=claude-haiku-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-haiku-5-5, effort=low, prompt=neutral (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 test functions, all pass / 0 failed / 0 skipped (5 effective) — `test_coverage=0.72` from `scores.json`
- **Build:** pass (compiles; tests build+run — `test_coverage=0.72 > 0`, `defect_rate=1.0`)
- **Lint:** pass — `code_quality=1.0` from `scores.json` (no warnings)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.go:handleCreate` + `store.go:Create`; `bookInput` has all four fields |
| R2 | GET /books lists all books | ✓ implemented | `server.go:handleList` + `store.go:List` |
| R3 | GET /books ?author= filter | ✓ implemented | `server.go:86` reads `author` query; `store.go:99` `WHERE LOWER(author)=LOWER(?)` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `server.go:handleGet`; `store.go:Get` returns `ErrNotFound` → 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.go:handleUpdate` + `store.go:Update` (404 on 0 rows) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.go:handleDelete` + `store.go:Delete`; 204 on success |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `store.go:9` `modernc.org/sqlite`; schema + INSERT/SELECT, not in-memory |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `writeJSON`/`writeError`; 201/200/204/400/404/500/503 used throughout |
| R9 | Validation: title and author required | ✓ implemented | `server.go:validateBook` rejects blank title/author → 400 |
| R10 | GET /health health-check | ✓ implemented | `server.go:handleHealth` pings DB, returns `{"status":"ok"}` or 503 |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — setup, run, test, endpoints, examples, errors |
| R12 | At least 3 unit/integration tests | ✓ implemented | `server_test.go` — 5 test functions; `test_coverage=0.72 > 0` |

## Build & Test

Scores read from `scores.json` (inline gate output); build/test/lint NOT re-run per skill guidance.

```text
scores.json:
  test_coverage   = 0.72   (tests built + ran, all pass)
  code_quality    = 1.0    (lint clean)
  defect_rate     = 1.0    (build+test succeeded)
  maintainability = 0.846
  idiomatic       = 0.9
  token_efficiency= 0.042
```

```text
go test ./...  (per README) — 5 test functions:
  TestBookLifecycle, TestListWithAuthorFilter, TestValidation, TestNotFound, TestHealth
  0 t.Skip / t.Skipf occurrences
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 420 (main 53, server 209, store 158) |
| Lines of code (tests) | 190 |
| Files (source) | 4 Go files + go.mod/go.sum + README.md |
| Dependencies | `modernc.org/sqlite` (sole direct dep) |
| Tests total | 5 functions (TestValidation has 7 sub-cases) |
| Tests effective | 5 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scored inline) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, no deductions:

1. [info] Hardened request decoding beyond spec (1 MiB cap, `DisallowUnknownFields`, trailing-data check)
2. [info] Graceful shutdown + configurable `ADDR`/`DB_PATH`
3. [info] `?author=` filter is exact full-string case-insensitive match (documented; acceptable per spec)

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=low_language=go_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                  # stored mechanical scores (do not re-run build/test)
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" server_test.go             # 5 test functions
```
