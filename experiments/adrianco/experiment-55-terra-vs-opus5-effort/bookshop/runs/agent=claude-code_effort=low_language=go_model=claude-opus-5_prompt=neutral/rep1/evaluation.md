# Evaluation: agent=claude-code effort=low language=go model=claude-opus-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-opus-5, agent=claude-code, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 test functions, all pass / 0 failed / 0 skipped (6 effective); `test_coverage=0.72` from scores.json
- **Build:** pass — `defect_rate=1.0` from scores.json (build + tests executed and passed)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** run-summary skill unavailable in this session; module layout described inline below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Clean run. A compact, idiomatic Go implementation using the stdlib `net/http` method-routing mux (Go 1.22+) and a pure-Go SQLite driver. Every pinned requirement is satisfied with test evidence, and no tests are skipped.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `server.go:22,78` createBook → `store.go:51` Create; `server_test.go:51` |
| R2 | GET /books lists all | ✓ implemented | `server.go:23,91` listBooks → `store.go:66` List; `server_test.go:105` |
| R3 | GET /books ?author= filter | ✓ implemented | `server.go:92` reads `author` query → `store.go:69` `WHERE author = ?`; `server_test.go:110` |
| R4 | GET /books/{id} single book | ✓ implemented | `server.go:24,100` getBook, 404 via ErrNotFound; `server_test.go:59,152` |
| R5 | PUT /books/{id} update | ✓ implemented | `server.go:25,117` updateBook → `store.go:102`; `server_test.go:130` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `server.go:26,138` deleteBook, 204; `store.go:119`; `server_test.go:144` |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7` `modernc.org/sqlite`, schema at `store.go:35` |
| R8 | JSON responses + status codes | ✓ implemented | `server.go:32` writeJSON; 201/200/204/400/404/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `server.go:63-70` decodeBook; `server_test.go:72` TestCreateValidation |
| R10 | GET /health | ✓ implemented | `server.go:21,44` health → store.Ping; `server_test.go:174` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` (2.8 KB) present |
| R12 | ≥3 unit/integration tests | ✓ implemented | 6 `TestXxx` funcs; `test_coverage=0.72` (> 0 ⇒ ran) |

Prompt factor `neutral` adds no discrete checkable instructions (it defers methodology to the agent and asks for demonstrating tests, which R12 already covers), so no `P*` requirements.

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.0208, "test_coverage": 0.72,
              "defect_rate": 1.0, "maintainability": 0.905, "idiomatic": 0.76}
# defect_rate=1.0 ⇒ `go test ./...` built and passed; test_coverage=0.72 ⇒ tests executed.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 525 (36 main + 152 server + 135 store + 202 test) |
| Files | 14 (incl. go.mod/go.sum/README) |
| Dependencies (go.sum lines) | 21 |
| Tests total | 6 funcs (+ subtests) |
| Tests effective | 6 (0 skipped) |
| Skip ratio | 0% |
| Build duration | not re-run (stored scores) |

## Findings

All findings are informational (no defects):

1. [info] Input hardening beyond spec — request-size cap, strict JSON decoding, year bounds.
2. [info] Pure-Go SQLite driver (modernc.org/sqlite) — no cgo needed.
3. [info] Low token_efficiency (0.0208) — metric observation, not a code defect.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=claude-code_effort=low_language=go_model=claude-opus-5_prompt=neutral/rep1
cat scores.json          # stored mechanical scores (build/test/lint)
grep -rE "t\.Skip" . --include="*.go" | wc -l   # 0 skips
go test ./...            # optional re-verify; defect_rate=1.0 already confirms pass
```
