# Evaluation: agent=codex language=go prompt=neutral · rep 2

## Summary

- **Factors:** language=go, agent=codex, model=gpt-5.6-luna, framework=unknown, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json); build not re-run
- **Lint:** pass — `code_quality=0.9556` (scores.json)
- **Architecture:** single-file `net/http` service (run-summary skill not registered; described below)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:100` createBook + INSERT; test `TestCreateAndGetBook` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:69` listBooks SELECT; test `TestListFiltersByAuthor` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:70-76` WHERE author=?; test `TestListFiltersByAuthor` |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:115` getBook; 404 at `main.go:122`; test `TestCreateAndGetBook` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:132` updateBook; 404 on 0 rows; test `TestValidationUpdateAndDelete` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:154` deleteBook → 204; test `TestValidationUpdateAndDelete` |
| R7 | Data stored in SQLite | ✓ implemented | `modernc.org/sqlite`, `main.go:215` opens `books.db`, CREATE TABLE `main.go:38` |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON`/`writeError` `main.go:204-212`; 201/200/204/400/404/500 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `main.go:186` rejects empty title/author → 400; test `TestValidationUpdateAndDelete` |
| R10 | GET /health | ✓ implemented | `main.go:61` health pings DB → 200 ok / 503 unhealthy |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run, Endpoints, Test sections |
| R12 | ≥3 tests | ✓ implemented | 3 test funcs in `main_test.go`; `test_coverage=0.664`, `defect_rate=1.0` |

## Build & Test

Not re-run per skill guidance — stored scores used as the build+test signal:

```text
scores.json: test_coverage=0.664, defect_rate=1.0, code_quality=0.9556,
             maintainability=0.9404, idiomatic=0.68, token_efficiency=0.0266
```

`defect_rate=1.0` ⇒ build + tests passed. `test_coverage=0.664` is real Go
statement coverage (3/3 tests pass). No `t.Skip` present (0 skipped).

Note: `_agent_stderr.log` shows the agent's own `go test` invocation was
sandbox-rejected (used `rm -f` in the command); this did not affect the final
scored build/test, which passed.

## Architecture

Single-file Go service (`main.go`, 226 lines). `Server` wraps `*sql.DB`;
`Handler()` registers Go 1.22+ method-pattern routes (`GET /books/{id}`, etc.)
on a `http.ServeMux`. Handlers share helpers `decodeInput` (validation),
`pathID` (path parsing), `writeJSON`/`writeError`. SQLite via
`modernc.org/sqlite` (pure-Go, cgo-free), `SetMaxOpenConns(1)` for serialized
writes. Clean separation, idiomatic error handling.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source) | 318 (main.go 226 + main_test.go 92) |
| Files | 12 (incl. logs/meta; 3 source: main.go, main_test.go, README) |
| Dependencies | go.sum: 51 lines (modernc.org/sqlite + transitive) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] `decodeInput` rejects any unknown JSON field with 400 (`main.go:181` DisallowUnknownFields)
2. [info] GET /health endpoint has no dedicated test (`main_test.go`)

No critical/high/medium findings. This is a complete, correct, idiomatic
implementation of the full spec.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-53-codex-bookshop/runs/agent=codex_language=go_prompt=neutral/rep2
cat scores.json                       # stored build/test/lint scores
go test ./...                         # 3 tests, all pass (if re-verifying)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
```
