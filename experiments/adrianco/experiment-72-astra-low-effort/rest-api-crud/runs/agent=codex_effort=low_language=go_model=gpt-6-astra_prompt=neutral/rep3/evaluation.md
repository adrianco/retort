# Evaluation: agent=codex effort=low language=go model=gpt-6-astra prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 test functions, 0 skipped (4 effective) — `test_coverage=0.756` from scores.json
- **Build:** pass — `defect_rate=1.0` from scores.json (build + tests ran and passed)
- **Lint:** pass — `code_quality=0.956` from scores.json
- **Architecture:** single-file `net/http` handler over an `*sql.DB` (SQLite); see below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:107-123` INSERT + 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `main.go:124-150` SELECT … ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:127-130` WHERE author = ? |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.go:166-177` sql.ErrNoRows → 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:181-188` UPDATE, 404 if RowsAffected=0 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:189-206` DELETE → 204 |
| R7 | SQLite / embedded DB | ✓ implemented | `main.go:16,29-48` go-sqlite3, CREATE TABLE |
| R8 | JSON + correct status codes | ✓ implemented | `main.go:50-57` writeJSON; 201/200/204/400/404/405/500/503 |
| R9 | Validation: title & author required | ✓ implemented | `main.go:85-88` trim + reject empty → 400 |
| R10 | GET /health | ✓ implemented | `main.go:93-103` PingContext → 200/503 |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, env vars, test cmds |
| R12 | ≥3 tests | ✓ implemented | `main_test.go` 4 tests (TestCRUD, TestAuthorFilter, TestValidationAndRouting, TestHealthAndPersistence) |

## Build & Test

Not re-run — stored scores used per skill guidance:

```text
scores.json: defect_rate=1.0 (build+tests passed), test_coverage=0.756,
             code_quality=0.956, maintainability=0.911, idiomatic=0.82
```

Skip scan (`grep -rEc "t\.Skip"`): 0 skips in main_test.go — all 4 tests effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 378 (main.go 234 + main_test.go 144) |
| Files (tracked) | main.go, main_test.go, go.mod, go.sum, README.md |
| Dependencies | 1 direct (github.com/mattn/go-sqlite3) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |

## Architecture

Single-package (`package main`) Go service. `API{db *sql.DB}` implements `http.ServeHTTP`,
routing by path/method manually (no framework). `openDB` creates the SQLite schema with
NOT NULL + trim CHECK constraints and `SetMaxOpenConns(1)`. Input decoding is centralized in
`input()` with `MaxBytesReader` and `DisallowUnknownFields`. (run-summary skill not invoked;
codebase is one file — structure is fully described here.)

## Findings

No defects. 2 informational notes (full list in `findings.jsonl`):

1. [info] Test suite exceeds the 3-test minimum with adversarial coverage (SQLi, oversize body, id overflow, persistence).
2. [info] Hardening beyond spec: MaxBytesReader, DisallowUnknownFields, Location header, DB CHECK constraints.

## Reproduce

```bash
cd "experiments/adrianco/experiment-72-astra-low-effort/rest-api-crud/runs/agent=codex_effort=low_language=go_model=gpt-6-astra_prompt=neutral/rep3"
cat scores.json
grep -rEc "t\.Skip\(|t\.Skipf\(" . --include="*.go"
# stored scores used in place of re-running: go build ./... && go test ./...
```
