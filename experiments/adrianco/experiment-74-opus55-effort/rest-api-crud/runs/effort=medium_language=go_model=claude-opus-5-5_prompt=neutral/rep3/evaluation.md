# Evaluation: effort=medium_language=go_model=claude-opus-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=claude-opus-5-5, prompt=neutral, effort=medium
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 test functions (12 validation subtests), 0 skipped (all effective) — `test_coverage=0.737`, `defect_rate=1.0` (build + tests passed)
- **Build:** pass (from `scores.json`: defect_rate=1.0)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:114 create` → `store.go:53 Create` (INSERT) |
| R2 | GET /books lists all | ✓ implemented | `handlers.go:128 list` → `store.go:64 List` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:67-70` WHERE author COLLATE NOCASE; `handlers.go:129` reads query param; `main_test.go:136` asserts filter |
| R4 | GET /books/{id} single (404) | ✓ implemented | `handlers.go:137 get` → `store.go:88 Get`; 404 via `ErrNotFound` (`handlers.go:143`) |
| R5 | PUT /books/{id} update | ✓ implemented | `handlers.go:154 update` → `store.go:98 Update`; 404 when RowsAffected==0 |
| R6 | DELETE /books/{id} | ✓ implemented | `handlers.go:175 delete` → `store.go:110 Delete`; 204 on success |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:8 modernc.org/sqlite`, schema `store.go:35`; `main_test.go:215` reopen test proves durability |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON` `handlers.go:221`; 201/200/204/404/400/422/405 across handlers |
| R9 | Validation: title+author required | ✓ implemented | `handlers.go:32 validate` rejects blank title/author (`main_test.go:163`); returns 422 (see finding) |
| R10 | GET /health | ✓ implemented | `handlers.go:106 health` pings DB, returns status; `main_test.go:65` |
| R11 | README setup + run | ✓ implemented | `README.md` — requirements, setup/run, test, endpoints, payload, errors, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 8 top-level `Test*` funcs in `main_test.go`; `test_coverage=0.737` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
code_quality:      1.000
test_coverage:     0.737   (build + tests passed; 0.0 would mean tests did not execute)
defect_rate:       1.000   (build + test succeeded)
maintainability:   0.854
idiomatic:         0.880
token_efficiency:  0.0133
```

Skip scan: `grep -E "t\.Skip\(|t\.Skipf\("` → 0 skips. All tests effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (Go source, incl. tests) | 658 |
| Lines of code (non-test source) | 405 |
| Files (source) | 4 .go + README + go.mod/go.sum |
| Dependencies (go.sum lines) | 50 (1 direct: modernc.org/sqlite) |
| Tests total (top-level funcs) | 8 |
| Tests effective | 8 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (read from scores; not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] R9 — validation returns 422, not the 400 implied by the task's verify note (requirement still satisfied; 422 is semantically valid)
2. [info] Robustness beyond spec — graceful shutdown, MaxBytes + DisallowUnknownFields, JSON 404/405 fallback, ISBN format validation
3. [info] Persistence verified across DB reopen (`main_test.go:215`)

No critical, high, or medium findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd experiments/adrianco/experiment-74-opus55-effort/rest-api-crud/runs/effort=medium_language=go_model=claude-opus-5-5_prompt=neutral/rep3
cat scores.json                                   # stored mechanical scores (not re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0
grep -rE "^func Test" main_test.go                # 8 test functions
# optional live check: go test ./...
```
