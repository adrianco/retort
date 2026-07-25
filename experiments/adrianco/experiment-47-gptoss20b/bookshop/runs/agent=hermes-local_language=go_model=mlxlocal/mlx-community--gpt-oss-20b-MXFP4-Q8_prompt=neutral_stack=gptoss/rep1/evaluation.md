# Evaluation: go · gpt-oss-20b-MXFP4-Q8 · hermes-local · neutral · rep 1

## Summary

- **Factors:** language=go, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok (repair task — prior attempt failed at requirement_coverage 0.92; now passing)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.9556 from scores.json
- **Architecture:** run-summary skill unavailable — single-file Go service (main.go) with gorilla/mux router + go-sqlite3; handlers + initDB; tests in main_test.go inject an in-memory DB via setTestDB.
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:75` createBookHandler INSERTs 4 fields, returns 201; tested `main_test.go:24` |
| R2 | GET /books lists all | ✓ implemented | `main.go:97` listBooksHandler SELECTs all |
| R3 | ?author= filter | ✓ implemented | `main.go:101-105` WHERE author=?; tested `main_test.go:51` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `main.go:124` getBookHandler; 404 at `main.go:131` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:141` updateBookHandler UPDATE + RowsAffected 404 |
| R6 | DELETE /books/{id} | ✓ implemented | `main.go:168` deleteBookHandler DELETE + 204/404 |
| R7 | SQLite persistence | ✓ implemented | `main.go:31` sql.Open("sqlite3", ...); schema `main.go:56` |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/404/400/204/500 across handlers; Content-Type set |
| R9 | title/author required | ✓ implemented | `main.go:81` and `main.go:149` reject empty with 400 |
| R10 | GET /health | ✓ implemented | `main.go:70` healthHandler returns {"status":"ok"}; tested `main_test.go:71` |
| R11 | README with setup/run | ✓ implemented | `README.md` — prerequisites, build, run, endpoints, testing |
| R12 | ≥3 tests that run | ✓ implemented | 3 Test funcs; test_coverage=0.37 (>0) |

## Build & Test

Not re-run — stored scores used per skill:

```text
scores.json: {"code_quality": 0.9556, "test_coverage": 0.37, "defect_rate": 1.0,
              "maintainability": 0.9388, "idiomatic": 0.68, "token_efficiency": 0.0081}
defect_rate=1.0  => build + tests succeeded
test_coverage=0.37 => genuine Go coverage (tests executed, all passed); 0 skips
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 264 (main.go 182 + main_test.go 82) |
| Files | 16 (incl. logs/meta) |
| Dependencies | gorilla/mux, mattn/go-sqlite3 (go.sum: 4 lines) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Coverage | 37% |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] strconv.Atoi error ignored in getBookHandler (`main.go:126`) — guarded by route regex
2. [low] Scan would fail on NULL year/isbn rows written outside the API (`main.go:114`)
3. [info] Coverage 37%: PUT/DELETE/validation-400 paths untested

## Reproduce

```bash
cd "<run_dir>"
cat scores.json                                          # stored mechanical scores
grep -rE "^func Test" main_test.go                       # 3 tests
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l  # 0 skips
go test ./...                                             # (optional) build+test
```
