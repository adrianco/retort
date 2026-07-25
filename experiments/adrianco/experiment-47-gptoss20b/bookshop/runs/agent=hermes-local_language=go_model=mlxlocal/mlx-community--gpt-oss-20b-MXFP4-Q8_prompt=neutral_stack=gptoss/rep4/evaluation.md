# Evaluation: gpt-oss-20b · go · hermes-local · rep 4

## Summary

- **Factors:** language=go, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok — repair task; all 12 requirements met, build + tests pass
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.956 from scores.json
- **Architecture:** `run-summary` skill unavailable — see inline notes below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

This was a REPAIR task: a prior attempt failed independent evaluation (build/tests
did not fully pass, and no README, per `FEEDBACK.md`). The repaired code now builds,
all five tests pass, a README with setup/run instructions exists, and every
requirement is satisfied. This rep carries a fuller test suite than rep1 — it adds
`TestUpdateAndDelete` and `TestValidation`, lifting coverage from 37% to 58.2%.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:73` createBookHandler, INSERT at `main.go:83`, 201 at `main.go:91` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:96` listBooksHandler, SELECT at `main.go:103` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:97,101` filters `WHERE author=?` |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:124` getBookHandler; 404 on ErrNoRows at `main.go:133` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:145` updateBookHandler, UPDATE at `main.go:161`; 404 if 0 rows at `main.go:167` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:177` deleteBookHandler, DELETE at `main.go:184`; 204/404 at `main.go:190,194` |
| R7 | SQLite/embedded DB storage | ✓ implemented | `main.go:11` go-sqlite3 driver, `main.go:27` sql.Open, schema `main.go:54` |
| R8 | JSON responses + status codes | ✓ implemented | Content-Type JSON on book routes; 201/200/404/400/204 codes set |
| R9 | Validate title & author required | ✓ implemented | `main.go:79` and `main.go:157` reject empty with 400 |
| R10 | GET /health | ✓ implemented | `main.go:38,67` healthHandler returns 200 (plain "OK") |
| R11 | README with setup/run | ✓ implemented | `README.md:18-32` setup, build, run instructions |
| R12 | >= 3 tests that run | ✓ implemented | `main_test.go` 5 tests; test_coverage=0.582 (>0), tests pass |

## Build & Test

Build/test not re-run — stored scores from `scores.json` are authoritative:

```text
scores.json: defect_rate=1.0 (build + tests succeeded)
             test_coverage=0.582 (tests executed and passed; 58.2% line coverage)
             code_quality=0.956, maintainability=0.962, idiomatic=0.58
```

```text
go test ./...  (5 tests, 0 skips)
  TestHealth              — GET /health returns 200
  TestCreateAndGetBook    — POST then GET by id, asserts 201/200 + title
  TestListBooksWithFilter — ?author= filter returns exactly the matching book
  TestUpdateAndDelete     — PUT updates fields, DELETE returns 204, then GET 404
  TestValidation          — POST without title returns 400
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, main.go + main_test.go) | 368 |
| Files (excl. .git) | 16 |
| Dependencies (go.sum entries) | 4 (gorilla/mux, mattn/go-sqlite3) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Line coverage | 58.2% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Line coverage 58.2% — 404/invalid-id/DB-error branches untested
2. [info] Health endpoint returns plain text "OK" rather than JSON
3. [info] Tests rebuild the route table instead of sharing main()'s wiring

## Architecture

`run-summary` skill unavailable in this environment. Structure is a single-file Go
service (`main.go`): `Book` struct, package-level `*sql.DB`, `initDB` schema
bootstrap, a gorilla/mux router with a `/books` subrouter wiring six routes to six
handlers. Tests live in `main_test.go` using `httptest` against in-memory SQLite via
a `newTestRouter` helper.

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=go_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep4
cat scores.json                                    # authoritative build/test/lint scores
grep -rE "^func Test" *.go                          # 5 tests
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go"  # 0 skips
```
