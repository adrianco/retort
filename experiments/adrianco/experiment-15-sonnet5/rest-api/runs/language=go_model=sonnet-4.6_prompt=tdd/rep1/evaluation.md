# Evaluation: language=go · model=sonnet-4.6 · prompt=tdd · rep 1

## Summary

- **Factors:** language=go, model=sonnet-4.6, prompt=tdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 9 test functions (12 incl. subtests), 0 failed, 0 skipped (all effective)
- **Build:** pass — `defect_rate=1.0` from `scores.json`
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Coverage:** `test_coverage=0.649` (64.9%) from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handler.go:handleCreateBook` → `store.go:create`; `TestCreateBook` |
| R2 | GET /books lists all | ✓ implemented | `handler.go:handleListBooks` → `store.go:list`; `TestListBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:list` `WHERE author = ?`; `TestListBooksAuthorFilter` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `handler.go:handleGetBook`, `errNotFound`→404; `TestGetBook`, `TestGetBookNotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `handler.go:handleUpdateBook` → `store.go:update`; `TestUpdateBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handler.go:handleDeleteBook` → `store.go:delete`; `TestDeleteBook` |
| R7 | Data stored in SQLite | ✓ implemented | `store.go` uses `modernc.org/sqlite`, `CREATE TABLE books` |
| R8 | JSON + appropriate status codes | ✓ implemented | `handler.go:writeJSON`; 201/200/204/400/404/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `handleCreateBook`/`handleUpdateBook` empty-check→400; `TestCreateBookValidation` (4 subtests) |
| R10 | GET /health | ✓ implemented | `handler.go:handleHealth` returns `{"status":"ok"}`; `TestHealthCheck` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup, Run, API, Tests sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 9 test functions in `handler_test.go`; `test_coverage=0.649>0` |

### Prompt factor (tdd)

The `prompt=tdd` factor asked for red/green/refactor discipline. The final artifact is consistent with test-first development: `_agent_stdout.log` narrates writing `handler_test.go` first ("all would have failed with no implementation") before the four source files. Per-test red/green cadence is not verifiable from the archived artifact (no git history) — see finding `tdd-1`. Not scored as a deduction.

## Build & Test

Scores read from `scores.json` (not re-run, per skill policy):

```text
defect_rate    = 1.0    # build + tests succeeded
test_coverage  = 0.649  # 64.9% statement coverage, tests executed & passed
code_quality   = 1.0    # lint/quality clean
maintainability= 0.891
idiomatic      = 0.9
```

Test suite (`go test ./...`) — 9 functions, static-analyzed:
```text
TestHealthCheck, TestCreateBook, TestCreateBookValidation (4 subtests),
TestListBooks, TestListBooksAuthorFilter, TestGetBook, TestGetBookNotFound,
TestUpdateBook, TestDeleteBook
0 skipped (grep t.Skip = 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, non-test) | 314 |
| Lines of code (tests) | 270 |
| Files (source + test) | 5 `.go` + README + go.mod/go.sum |
| Direct dependencies | 1 (`modernc.org/sqlite`; 10 transitive) |
| Tests total (functions) | 9 |
| Tests effective | 9 (0 skipped) |
| Skip ratio | 0% |
| Coverage | 64.9% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] `json.Encode` error ignored in `writeJSON` (`handler.go`)
2. [info] Coverage 64.9% — `main.go` bootstrap and 500-error branches unexercised
3. [info] PUT is full-replace (requires title+author), not PATCH-style partial update
4. [info] TDD prompt: test-first evidenced; per-test red/green cadence not verifiable post-hoc

No critical, high, or medium findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=go_model=sonnet-4.6_prompt=tdd/rep1
# scores read from scores.json (build/test not re-run per skill policy)
cat scores.json
# to reproduce build+test locally:
go test ./... -cover
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # -> 0
grep -rE "^func Test" . --include="*.go"                      # -> 9 funcs
```
