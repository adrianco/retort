# Evaluation: agent=codex language=go prompt=neutral · rep 3

## Summary

- **Factors:** language=go, agent=codex, model=gpt-5.6-luna, prompt=neutral, framework=net/http
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint/Quality:** pass — code_quality=0.956, maintainability=0.916, idiomatic=0.72 (from scores.json)
- **Coverage:** test_coverage=0.587 (from scores.json)
- **Architecture:** single-file `net/http` server + SQLite (modernc.org/sqlite, pure-Go, no cgo); `run-summary` skill unavailable, not generated
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:97-112` INSERT, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `main.go:90-96`, `listBooks` `main.go:176-198` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:91`, `main.go:179-182` WHERE author=? |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.go:125-135`, `findBook`; 404 on `sql.ErrNoRows` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:136-155` UPDATE, 404 if 0 rows |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:156-166` DELETE, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:14,34,56-64` modernc.org/sqlite + CREATE TABLE |
| R8 | JSON + appropriate status codes | ✓ implemented | `writeJSON` `main.go:215`; 201/200/204/400/404/405/500 used |
| R9 | Validation: title & author required | ✓ implemented | `validateBook` `main.go:172-174`, 400 in POST/PUT |
| R10 | GET /health | ✓ implemented | `main.go:69-76` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — run, env vars, endpoints, curl example |
| R12 | ≥3 tests | ✓ implemented | `main_test.go` — 4 Test functions, 0 skips |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per evaluate-run skill):

```text
defect_rate    = 1.0     # build + tests passed
test_coverage  = 0.587   # statement coverage
code_quality   = 0.956
maintainability= 0.916
idiomatic      = 0.72
```

Test inventory (`grep '^func Test' main_test.go`): TestCreateGetAndFilterBooks,
TestValidationAndNotFound, TestUpdateAndDeleteBook, TestHealth — 4 tests, 0 `t.Skip`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 319 (main.go 228, main_test.go 91) |
| Files (excl .git) | 12 |
| Direct dependencies | 1 (modernc.org/sqlite) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Coverage | 58.7% |

## Findings

Full list in `findings.jsonl` (no critical/high/medium):

1. [low] JSON decoder does not reject unknown/extra fields — `main.go:206-213`
2. [low] PUT full-replace semantics untested (omitted fields zeroed) — `main.go:145`
3. [info] Configurable PORT / DATABASE_PATH env vars (beyond spec) — `main.go:30-47`

## Reproduce

```bash
cd experiments/adrianco/experiment-53-codex-bookshop/runs/agent=codex_language=go_prompt=neutral/rep3
cat scores.json                       # mechanical scores (build/test/quality)
grep -c '^func Test' main_test.go      # test count
grep -rE 't\.Skip' . --include='*.go'  # skip count (0)
# optional full re-run: go test ./...
```
