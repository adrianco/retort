# Evaluation: agent=hermes-local_language=go_prompt=none_stack=s7 · rep 3

## Summary

- **Factors:** language=go, agent=hermes-local (model Qwen3.6-35B-A3B), prompt=none, stack=s7, framework=gin
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective) — build+test succeeded (defect_rate=1.0), coverage 61.2%
- **Build:** pass (from retort.db/scores.json — not re-run)
- **Lint:** pass — code_quality=0.956 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.go:74 CreateBook` + INSERT `app.go:91`; test `app_test.go:43` |
| R2 | GET /books lists all books | ✓ implemented | `app.go:118 ListBooks`; test `app_test.go:143` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.go:119-124` filtered query; test `app_test.go:180` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.go:165 GetBook`, 404 at `app.go:177-179`; tests `app_test.go:220,258` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.go:190 UpdateBook`; tests `app_test.go:276,323` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.go:245 DeleteBook`; tests `app_test.go:350,384` |
| R7 | Data stored in SQLite | ✓ implemented | `app.go:39 sql.Open("sqlite3", ...)`, table DDL `app.go:45-52` |
| R8 | JSON responses + correct status codes | ✓ implemented | c.JSON with 201/200/400/404/500 throughout `app.go`; asserted across tests |
| R9 | Validation: title & author required | ✓ implemented | `app.go:82-89` (create), `app.go:204-211` (update); tests `app_test.go:89,116` |
| R10 | GET /health | ✓ implemented | `app.go:69 HealthCheck`, route `app.go:285`; test `app_test.go:402` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, run, endpoints, curl examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 16 test functions in `app_test.go`; test_coverage=0.612 (>0) |

## Build & Test

Mechanical scores read from `scores.json` (retort scorers already ran the toolchain — not re-run):

```text
test_coverage   = 0.612   (build + tests ran; 61.2% coverage)
defect_rate     = 1.0     (build + test succeeded)
code_quality    = 0.9556  (lint/quality)
maintainability = 0.9333
idiomatic       = 0.4
token_efficiency= 0.029
```

Agent's own report (`_agent_stdout.log`): "All 16 tests pass." No `t.Skip` present in the suite.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 882 (app.go 298, app_test.go 584) |
| Files | 13 (incl. built `bookapi` binary) |
| Dependencies (go.sum lines) | 88 |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Tests set an invalid Content-Type header `"http://json"` — passes only because `gin.ShouldBindJSON` ignores it (`app_test.go:62,108,...`)
2. [info] Dead/incorrect first request in `TestGetBook` (`app_test.go:237-239`) — result discarded
3. [info] Low idiomatic score (0.4) from duplicated row-scan loop and repeated validation blocks (`app.go:131-154`, `app.go:82-89` vs `204-211`)

No critical/high/medium findings: the spec is fully implemented and the test suite builds and passes.

## Reproduce

```bash
cd "experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=go_prompt=none_stack=s7/rep3"
cat scores.json                      # mechanical scores (build/test/lint already run by retort)
grep -rEc "t\.Skip\(|t\.Skipf\(" . --include="*.go"   # skip count → 0
grep -cE "^func Test" app_test.go    # test function count → 17 (incl. TestMain)
# Optional re-verify (skill says prefer stored scores; toolchain needs CGO):
# go test -v ./...
```
