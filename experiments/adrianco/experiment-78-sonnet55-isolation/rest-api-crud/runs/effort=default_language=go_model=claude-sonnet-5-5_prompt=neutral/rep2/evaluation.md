# Evaluation: effort=default language=go model=claude-sonnet-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, prompt=neutral, effort=default (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, denominator 12)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective) — `defect_rate=1.0`, `test_coverage=0.787`
- **Build:** pass (from `scores.json`: `defect_rate=1.0`, `test_coverage=0.787` ⇒ build + tests ran and passed; not re-run)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

Neutral prompt factor (`prompts/neutral.md`) prescribes no methodology beyond "include tests"; it adds no extra checkable `P*` requirements.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:79 server.create` → `store.go:47 Store.Create`; `main_test.go:37 TestCRUD` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:93 server.list` → `store.go:57 Store.List`; `main_test.go:82 TestListFilter` |
| R3 | GET /books ?author= filter | ✓ implemented | `store.go:60 WHERE author = ?`; `main_test.go:88` filters to X |
| R4 | GET /books/{id} single book | ✓ implemented | `main.go:102 server.get` → `store.go:80 Store.Get` (404 on `sql.ErrNoRows`); `main_test.go:46,56` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:115 server.update` → `store.go:90 Store.Update` (404 if 0 rows); `main_test.go:49` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:132 server.delete` → `store.go:102 Store.Delete`; `main_test.go:53,59` |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:7,26` `modernc.org/sqlite`, `sql.Open("sqlite", dsn)`, real `books` table |
| R8 | JSON responses + status codes | ✓ implemented | `main.go:29 writeJSON`; 201/200/204/400/404/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `main.go:66-70 decode` rejects empty title/author (400); `main_test.go:64 TestValidation` |
| R10 | GET /health endpoint | ✓ implemented | `main.go:18` returns `{status:ok}`; `main_test.go:28 TestHealth` |
| R11 | README with setup/run | ✓ implemented | `README.md` documents `go run .`, env vars, `go test`, endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | 4 test funcs (`main_test.go:28,35,64,82`), `test_coverage=0.787 > 0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per evaluate-run step 2):

```text
scores.json: code_quality=1.0, test_coverage=0.787, defect_rate=1.0,
             maintainability=0.853, idiomatic=0.77, token_efficiency=0.074
```

`defect_rate=1.0` and `test_coverage=0.787` (>0) ⇒ `go build` + `go test` executed and all tests passed at 78.7% statement coverage. DB cross-check (`retort.db`, most recent completed rep-2 row) agrees: `code_quality=1.0`, `defect_rate=1.0`, `requirement_coverage=1.0`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | ~270 (main.go 160 + store.go 111) |
| Test LOC | 96 (main_test.go) |
| Source files | 3 (.go) + README + go.mod/go.sum |
| Direct dependencies | 1 (`modernc.org/sqlite`; 9 indirect) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Statement coverage | 78.7% |
| Cost / duration / turns (DB) | $0.207 / 75.2s / 8 turns |

## Findings

Top items (full list in `findings.jsonl`):

1. [info] Input validation and body cap exceed the spec — negative-year rejection (`main.go:71`) and 1 MiB body cap (`main.go:60`).

No critical/high/medium/low findings: all 12 requirements implemented, build+tests pass, zero skipped tests.

## Reproduce

```bash
cd "$(dirname "$0")"   # this run_dir
cat scores.json                                   # mechanical scores (build/test/lint) — not re-run
grep -rEn "^func Test" . --include="*.go"         # 4 test functions
grep -rEn "t\.Skip" . --include="*.go" | wc -l    # 0 skips
# DB cross-check:
db=$(d="$PWD"; for i in 1 2 3 4 5; do d="$(cd "$d/.." && pwd)"; [ -f "$d/retort.db" ] && { echo "$d/retort.db"; break; }; done)
sqlite3 -readonly "$db" "SELECT rr.metric_name, rr.value FROM run_results rr JOIN experiment_runs er ON er.id=rr.run_id WHERE json_extract(er.run_config_json,'\$.language')='go' AND json_extract(er.run_config_json,'\$.model')='claude-sonnet-5-5' AND er.replicate=2 AND er.status='completed' ORDER BY er.finished_at DESC;"
```
