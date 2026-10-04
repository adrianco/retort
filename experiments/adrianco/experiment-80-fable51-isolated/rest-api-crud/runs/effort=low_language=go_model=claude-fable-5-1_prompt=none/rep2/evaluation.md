# Evaluation: effort=low_language=go_model=claude-fable-5-1_prompt=none · rep 2

## Summary

- **Factors:** language=go, model=claude-fable-5-1, prompt=none, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 test functions, 0 skipped (6 effective); build+test succeeded
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.9556` (scores.json)
- **Architecture:** single-package Go service (`main.go` + `main_test.go`); `run-summary` not invoked (small two-file codebase, structure inlined below)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Scores (from `scores.json`): test_coverage=0.736, defect_rate=1.0, code_quality=0.9556, maintainability=0.9978, idiomatic=0.87, token_efficiency=0.0904.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:112` createBook, INSERT of title/author/year/isbn |
| R2 | GET /books lists all | ✓ implemented | `main.go:128` listBooks returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:131-134` adds `WHERE author = ?` |
| R4 | GET /books/{id} single, 404 | ✓ implemented | `main.go:158` getBook; 404 at `main.go:167-169` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:178` updateBook, UPDATE; 404 when 0 rows |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:202` deleteBook; 204/404 |
| R7 | Data in SQLite / embedded DB | ✓ implemented | `main.go:13` modernc.org/sqlite; schema at `main.go:28` |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON` `main.go:64`; 201/200/404/400/204 used |
| R9 | Validation: title+author required | ✓ implemented | `main.go:82-91` decodeBook rejects empty title/author with 400 |
| R10 | GET /health | ✓ implemented | `main.go:104` health, pings DB, returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` Setup + Run + Endpoints sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 tests in `main_test.go`; test_coverage=0.736 (>0) |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill step 2).

```text
defect_rate = 1.0        # build + tests succeeded
test_coverage = 0.736    # tests executed; 73.6% coverage
code_quality  = 0.9556   # lint/quality
```

Tests (`main_test.go`): TestHealth, TestCreateAndGetBook, TestCreateValidation,
TestListWithAuthorFilter, TestUpdateBook, TestDeleteBook. 0 skips
(`grep t.Skip` = 0). Tests use `httptest` against an in-memory SQLite DB.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.go) | 235 |
| Lines of code (main_test.go) | 140 |
| Source files (.go) | 2 |
| Direct dependencies | 1 (modernc.org/sqlite) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`:

1. [low] README states Go 1.22+ but go.mod pins go 1.26.6 (`README.md:9` vs `go.mod:3`)
2. [info] Uses stdlib net/http 1.22 method-pattern routing, no external framework
3. [info] Request body size capped (1 MiB) and /health pings the DB

## Reproduce

```bash
cd "experiments/adrianco/experiment-80-fable51-isolated/rest-api-crud/runs/effort=low_language=go_model=claude-fable-5-1_prompt=none/rep2"
cat scores.json                                  # mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json                   # pinned 12-item checklist
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count = 0
grep -rE "func Test" main_test.go                # 6 tests
```
