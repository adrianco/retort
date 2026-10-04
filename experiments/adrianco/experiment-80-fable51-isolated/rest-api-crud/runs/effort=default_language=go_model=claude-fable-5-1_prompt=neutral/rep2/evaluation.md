# Evaluation: rest-api-crud effort=default language=go model=claude-fable-5-1 prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-fable-5-1, prompt=neutral, effort=default (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 test functions, 0 skipped (all effective) — passed (test_coverage=0.731 from scores.json)
- **Build:** pass — from scores.json (`test_coverage`>0 ⇒ build succeeded; not re-run)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:68 createBook` → `store.go:62 Create` (INSERT) |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:82 listBooks` → `store.go:77 List` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `store.go:80-83` WHERE author COLLATE NOCASE; `handlers_test.go:151` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `handlers.go:91 getBook`; `store.go:108` maps ErrNoRows→404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `handlers.go:104 updateBook` → `store.go:114 Update`; `handlers_test.go:175` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `handlers.go:121 deleteBook` → `store.go:132 Delete` (204) |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:9,42 modernc.org/sqlite`; `TestPersistsAcrossReopen` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `writeJSON` 201/200/204/400/404/422; `handlers.go:181` |
| R9 | Validation: title and author required | ✓ implemented | `handlers.go:24-40 validate()`; `TestCreateValidation` (422) |
| R10 | GET /health health check | ✓ implemented | `handlers.go:60 health` pings DB; `TestHealth` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, env vars, tests, API table, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 8 `Test*` functions in `handlers_test.go`; test_coverage=0.731 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per evaluate-run Step 2):

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.0920, "test_coverage": 0.731,
              "defect_rate": 1.0, "maintainability": 0.8984, "idiomatic": 0.9}
```

`test_coverage=0.731` (>0 ⇒ `go build` + `go test ./...` ran and passed, 73.1% coverage);
`defect_rate=1.0` ⇒ build+test succeeded; `code_quality=1.0` ⇒ clean lint. Skip scan
(`t.Skip`/`t.Skipf`) found 0 skipped tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 390 (main.go + handlers.go + store.go) |
| Test LOC | 256 |
| Files (source, excl. .git) | 15 (incl. go.mod/go.sum, README) |
| Dependencies (go.mod require) | 9 (1 direct: modernc.org/sqlite; 8 indirect) |
| Tests total | 8 functions |
| Tests effective | 8 (0 skipped) |
| Skip ratio | 0% |
| Coverage | 73.1% |

## Findings

All findings are info-level (see `findings.jsonl`):

1. [info] Validation failures return 422 rather than the 400 the task text implies — semantically correct; R9 still satisfied.
2. [info] Production-grade extras beyond spec: graceful shutdown, 1 MiB body cap, `Location` header, persistence-across-reopen test.

No requirement-missing, build, test, or skipped-test findings.

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=default_language=go_model=claude-fable-5-1_prompt=neutral/rep2"
cat scores.json                                            # mechanical scores (build/test/lint)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l # skip count (0)
grep -rE "^func Test" handlers_test.go | wc -l             # test count (8)
# Optional re-verify (evaluate-run says do NOT normally re-run): go test ./...
```
