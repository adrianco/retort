# Evaluation: agent=hermes-local_language=go_prompt=none_stack=s6 · rep 1

## Summary

- **Factors:** language=go, agent=hermes-local (Qwen3.6-35B-A3B), prompt=none, stack=s6, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 top-level funcs / ~13 subtests passed, 0 failed, 0 skipped
- **Build:** pass (defect_rate=1.0 from scores.json — build+test gate succeeded)
- **Lint:** pass — code_quality=0.9556 from scores.json
- **Architecture:** summary skill unavailable (not registered this session)
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 1 info)

Scores from `scores.json`: test_coverage=0.299, code_quality=0.9556, defect_rate=1.0,
maintainability=0.8628, idiomatic=0.45, token_efficiency=0.0291.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.go:220` POST handler → `CreateBook` (app.go:80); `TestCreateBook` |
| R2 | GET /books lists all | ✓ implemented | `app.go:255` → `ListBooks` (app.go:119); `TestListBooks/list all` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:256` `c.Query("author")` → LIKE filter app.go:123-127; `TestListBooks/filter by author` |
| R4 | GET /books/{id} single, 404 if absent | ✓ implemented | `app.go:274` → `GetBook`; 404 on not-found app.go:286-290; `TestGetBook` (both cases) |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.go:302` → `UpdateBook` (app.go:155); `TestUpdateBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.go:352` → `DeleteBook` (app.go:184); `TestDeleteBook` verifies removal |
| R7 | SQLite / embedded DB | ✓ implemented | `go-sqlite3` (app.go:12), `NewDatabase` opens sqlite3, CREATE TABLE app.go:58-65 |
| R8 | JSON responses + correct status codes | ✓ implemented | 201 (app.go:251), 200, 400, 404, 500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `binding:"required"` (app.go:26-27) + explicit checks app.go:230-241; `TestCreateBookValidation` |
| R10 | GET /health | ✓ implemented | `app.go:212` returns `{"status":"healthy"}`; `TestHealthCheck` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — prerequisites, `go mod tidy`, `go run app.go`, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 7 test funcs in `app_test.go`; test_coverage=0.299 (>0, tests executed) |

No requirement gaps. Caveat on test *effectiveness*: the tests validate a router
duplicated inside `setupTestRouter` (app_test.go:23-158), not `app.go`'s own
`main()` handlers, so the passing tests do not cover the production wiring
(reflected in the 29.9% coverage). See findings.

## Build & Test

Not re-run — mechanical scores read from `scores.json` per skill Step 2:

```text
defect_rate    = 1.0    → go build + go test succeeded (test gate passed)
test_coverage  = 0.299  → tests executed; ~30% statement coverage
code_quality   = 0.9556 → lint/quality gate passed
```

Agent's own report (`_agent_stdout.log`): "Tests: 7/7 passing". The stdout also
records a benign verifier note — the agent's attempt to rewrite `./go.mod` was
refused as a "sensitive path"; `go.mod`/`go.sum` are nonetheless present and the
build passed.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.go) | 385 |
| Lines of code (app_test.go) | 390 |
| Files (total, incl. build meta) | 13 |
| Dependencies (go.sum lines) | 88 |
| Tests total (top-level funcs) | 7 |
| Tests effective (passed+failed) | 7 (0 skipped) |
| Skip ratio | 0% |
| Test coverage | 29.9% |
| Tokens (total / api_calls) | 433,861 / 19 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [medium] Tests exercise a duplicated router, not `app.go`'s real handlers — `app_test.go:23-158` re-declares routes; production handlers uncovered (coverage 29.9%).
2. [low] Unreachable validation branches in PUT (`app.go:321,327`); partial PUT blanks omitted fields via full-row UPDATE (`app.go:155-181`).
3. [low] Test coverage 29.9% despite green build/tests — DB layer covered, HTTP layer not.
4. [info] `run-summary` skill unavailable this session; no `summary/` produced.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s6/rep1
cat scores.json          # mechanical scores (build/test/lint already run by retort)
go test -v ./...         # optional: re-run tests (build+test)
grep -rE "t\.Skip\(" . --include="*.go" | wc -l   # skip count (0)
```
