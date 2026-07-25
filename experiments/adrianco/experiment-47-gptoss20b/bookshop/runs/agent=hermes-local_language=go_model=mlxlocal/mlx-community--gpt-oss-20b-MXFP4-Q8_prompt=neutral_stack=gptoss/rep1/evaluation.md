# Evaluation: gpt-oss-20b · go · hermes-local · rep 1

## Summary

- **Factors:** language=go, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok — repair task; all 12 requirements met, build + tests pass
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.956 from scores.json
- **Architecture:** `run-summary` skill unavailable — see inline notes below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

This was a REPAIR task: a prior attempt failed independent evaluation (build/tests
did not fully pass, requirement_coverage 0.92 per `FEEDBACK.md`). The repaired code
now builds, all three tests pass, and every requirement is satisfied.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:75` createBookHandler, INSERT at `main.go:85`, 201 at `main.go:93` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:97` listBooksHandler, SELECT at `main.go:104` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:98,102` filters `WHERE author=?` |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:124` getBookHandler; 404 on ErrNoRows at `main.go:131` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:141` updateBookHandler, UPDATE at `main.go:153`; 404 if 0 rows |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:168` deleteBookHandler, DELETE at `main.go:171`; 204/404 |
| R7 | SQLite/embedded DB storage | ✓ implemented | `main.go:10` go-sqlite3 driver, `main.go:31` sql.Open, schema `main.go:56` |
| R8 | JSON responses + status codes | ✓ implemented | Content-Type JSON throughout; 201/200/404/400/204 codes set |
| R9 | Validate title & author required | ✓ implemented | `main.go:81` and `main.go:149` reject empty with 400 |
| R10 | GET /health | ✓ implemented | `main.go:42,70` healthHandler returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md:22-38` setup, build, run instructions |
| R12 | >= 3 tests that run | ✓ implemented | `main_test.go` 3 tests; test_coverage=0.37 (>0), tests pass |

## Build & Test

Build/test not re-run — stored scores from `scores.json` are authoritative:

```text
scores.json: defect_rate=1.0 (build + tests succeeded)
             test_coverage=0.37 (tests executed and passed; 37% line coverage)
             code_quality=0.956, maintainability=0.939, idiomatic=0.68
```

```text
go test ./...  (3 tests, 0 skips)
  TestCreateAndGetBook   — POST then GET by id, asserts 201/200 + title
  TestListBooksWithFilter — ?author= filter returns exactly the matching book
  TestHealthEndpoint      — GET /health returns 200 + {"status":"ok"}
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, main.go + main_test.go) | 264 |
| Files (excl. .git) | 16 |
| Dependencies (go.sum entries) | 4 (gorilla/mux, mattn/go-sqlite3) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Line coverage | 37% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Test coverage 37% — update/delete/get-404/validation paths untested
2. [low] Input validation (R9) implemented but not asserted by any test
3. [info] Tests build ad-hoc routers instead of exercising the production route table

## Architecture

`run-summary` skill unavailable in this environment. Structure is a single-file Go
service (`main.go`): `Book` struct, package-level `*sql.DB` with a `setTestDB` seam
for tests, `initDB` schema bootstrap, gorilla/mux router wiring six routes to six
handlers. Tests live in `main_test.go` using `httptest` against in-memory SQLite.

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=go_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep1
cat scores.json                                    # authoritative build/test/lint scores
grep -rE "^func Test" *.go                          # 3 tests
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go"  # 0 skips
```
