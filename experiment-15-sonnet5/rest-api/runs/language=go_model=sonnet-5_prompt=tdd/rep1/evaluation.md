# Evaluation: language=go_model=sonnet-5_prompt=tdd · rep 1

## Summary

- **Factors:** language=go, model=sonnet-5, prompt=tdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Prompt (tdd):** 4/4 followed (2 implemented via test-first structure, 2 consistent-but-self-reported)
- **Tests:** 20 passed / 0 failed / 0 skipped (20 effective) — 18 top-level funcs + 2 table subtests
- **Build:** pass (test_coverage=0.696 & defect_rate=1.0 from scores.json ⇒ build + tests green)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Coverage:** 69.6% (scores.json test_coverage)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:29 handleCreateBook` → `store.go:52 CreateBook`; `TestCreateBook` |
| R2 | GET /books lists all books | ✓ implemented | `handlers.go:50 handleListBooks` → `store.go:84 ListBooks`; `TestListBooksAndFilterByAuthor` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:89-90` `WHERE author = ?`; `TestStoreListBooksFilterByAuthor` |
| R4 | GET /books/{id} single, 404 | ✓ implemented | `handlers.go:62 handleGetBook`; `TestGetBookByID`, `TestGetBookNotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:83 handleUpdateBook` → `store.go:113 UpdateBook`; `TestUpdateBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.go:114 handleDeleteBook` → `store.go:133 DeleteBook`; `TestDeleteBook` |
| R7 | SQLite / embedded DB | ✓ implemented | `store.go:7,21` `modernc.org/sqlite`, real `CREATE TABLE books` |
| R8 | JSON + correct status codes | ✓ implemented | `writeJSON` sets Content-Type; 201/200/204/400/404 used across handlers |
| R9 | Validation: title & author required | ✓ implemented | `handlers.go:135 validateBook`; `TestCreateBookValidation`, `TestUpdateBookValidation` |
| R10 | GET /health | ✓ implemented | `handlers.go:15,25 handleHealth`; `TestHealthCheck` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, env vars, API table, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 20 effective tests across `store_test.go` + `handlers_test.go`; test_coverage=0.696 |

### Prompt instructions (tdd)

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | Write a failing test before implementation | ✓ implemented | `_agent_stdout.log`: "built test-first throughout … confirmed red via build failures before implementing"; layered store+handler test files |
| P2 | Minimum code to pass each test | ✓ implemented | Handlers/store are lean, no speculative endpoints; scope matches tests |
| P3 | Refactor after each green pass | ~ cannot-verify | No commit history retained in `run_dir`; final code is clean/refactored but cadence unobservable |
| P4 | Tight red/green/refactor cycle | ~ cannot-verify | Same — self-reported only; final artifacts are consistent with it |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.696   # build + tests pass; 69.6% line coverage
defect_rate   = 1.0     # build + test succeeded
code_quality  = 1.0     # lint/quality
maintainability = 0.879
idiomatic     = 0.73
```

Test inventory (grepped, 0 skips):

```text
store_test.go     7 tests  (store CRUD + not-found, in-memory SQLite)
handlers_test.go 11 tests  (HTTP CRUD, health, validation table [2 cases], 404s)
effective = 20 passed / 0 failed / 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, non-test .go) | 341 |
| Lines of code (tests) | 345 |
| Go source files | 6 (4 impl + 2 test) |
| Dependencies (go.sum lines) | 21 (all indirect; only `modernc.org/sqlite` direct-use) |
| Tests total | 20 |
| Tests effective | 20 |
| Skip ratio | 0% |
| Coverage | 69.6% |

## Findings

Top 5 by severity (full list in `findings.jsonl`) — no high/critical:

1. [low] `cov-2` — 400 branches for malformed JSON body and non-numeric id path are untested (`handlers.go:32-34`, `:64-67`)
2. [low] `gomod-1` — `go.mod` pins `go 1.26.4` but README says Go 1.22+ (`go.mod:3` vs `README.md:10`)
3. [info] `cov-1` — coverage 69.6%; server bootstrap (`main.go`) and 500 branches unexercised
4. [info] `enh-1` — env-configurable addr/db path beyond spec (`main.go:10-18`)
5. [info] `tdd-1` — TDD discipline self-reported, not verifiable from final artifacts

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=go_model=sonnet-5_prompt=tdd/rep1
cat scores.json                                   # mechanical scores (build/test/lint)
grep -rnE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count = 0
grep -rhoE "^func Test[A-Za-z0-9_]+" *_test.go | wc -l        # 18 test funcs
# optional live re-run (skill says don't; scores.json already has them):
# go test ./...
```
