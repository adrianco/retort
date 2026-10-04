# Evaluation: rest-api-crud · agent=codex effort=low language=go model=gpt-6-astra prompt=neutral · rep 3

## Summary

- **Factors:** language=go, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral, framework=unknown (stdlib `net/http`)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** passed (test_coverage=0.734, defect_rate=1.0 from scores.json) / 0 failed / 0 skipped — 5 test functions, all effective
- **Build:** pass — from `test_coverage=0.734` (>0 ⇒ build+tests executed and passed); not re-run
- **Lint:** pass — `code_quality=0.9556` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:209` INSERT; `main_test.go:38` asserts 201 + fields |
| R2 | GET /books lists all | ✓ implemented | `main.go:157` `API.list`; `main_test.go:69` empty→`[]`, then 3 books |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:160-163` `WHERE author = ?`; `main_test.go:78` filter cases |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `main.go:108-113` `API.get`; `main_test.go:62/128` 200 + 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:219-232` UPDATE; `main_test.go:53` update persisted |
| R6 | DELETE /books/{id} | ✓ implemented | `main.go:116-129` DELETE, 204/404; `main_test.go:58` |
| R7 | SQLite / embedded DB | ✓ implemented | `main.go:19,39-58` go-sqlite3 + schema; `main_test.go:141` persistence across reopen |
| R8 | JSON responses + status codes | ✓ implemented | `main.go:60-70` `respond`/`fail`; codes 201/200/204/400/404/405/413/500/503 |
| R9 | Validation: title & author required | ✓ implemented | `main.go:201-206` trim + reject empty (400); `main_test.go:98` many 400 cases |
| R10 | GET /health | ✓ implemented | `main.go:78-89` health + DB ping; `main_test.go:124/138` 200 + 503 |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, env vars, API table, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 5 `func Test*` in `main_test.go`; test_coverage=0.734>0 |

## Build & Test

Not re-run — stored scores used per skill guidance (`scores.json` present):

```text
test_coverage = 0.734   # >0 ⇒ build + all tests executed and passed
defect_rate   = 1.0     # build+test succeeded
code_quality  = 0.9556  # lint/quality (Lint: pass)
maintainability = 0.9632
idiomatic     = 0.72
```

Skip scan (`grep -rEc 't\.Skip\(|t\.Skipf\('`): 0 skips in main.go and main_test.go.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 444 (main.go 283 + main_test.go 161) |
| Files (excl. .git) | 13 (incl. build artifacts) — 5 tracked source/doc/module files |
| Dependencies | 1 (`github.com/mattn/go-sqlite3`) |
| Tests total | 5 functions |
| Tests effective | 5 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level enhancements, no deductions:

1. [info] Parameterized SQL with an explicit `' OR 1=1--` injection test
2. [info] Strict request hardening: 1 MiB body cap, DisallowUnknownFields, trailing-token rejection, 405+Allow
3. [info] Graceful shutdown + server Read/Write/Idle timeouts

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-72/runs/agent=codex_effort=low_language=go_model=gpt-6-astra_prompt=neutral/rep3"
cat scores.json                                   # stored build/test/lint scores
grep -rEc 't\.Skip\(|t\.Skipf\(' . --include='*.go'
# optional re-run (skill says prefer stored scores): go test ./...
```
