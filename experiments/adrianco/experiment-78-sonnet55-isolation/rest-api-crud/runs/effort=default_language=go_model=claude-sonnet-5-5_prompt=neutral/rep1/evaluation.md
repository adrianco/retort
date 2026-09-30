# Evaluation: effort=default·language=go·model=claude-sonnet-5-5·prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=claude-sonnet-5-5, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 test functions, 0 skipped (4 effective) — build + tests passed (`test_coverage=0.768`, `defect_rate=1.0` from `scores.json`)
- **Build:** pass — from stored scores (not re-run)
- **Lint:** pass — `code_quality=1.0` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:40,97` → `store.go:44` INSERT; `main_test.go:37` asserts 201 |
| R2 | GET /books lists all | ✓ implemented | `main.go:41,110` → `store.go:54`; `main_test.go:100` len==3 |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:111` reads `author` query; `store.go:57-60` WHERE author=?; `main_test.go:101` len==2 |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.go:42,119` → `store.go:77`; 404 at `main.go:126`; `main_test.go:60` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:43,135` → `store.go:88` UPDATE; `main_test.go:52` asserts 200 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:44,155` → `store.go:94` DELETE, 204; `main_test.go:57` |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:6,23` `modernc.org/sqlite`, real table schema `store.go:28-34` |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON` `main.go:50`; 201/200/404/400/204/500 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `main.go:76-79` reject empty (400); `main_test.go:71-80` covers missing/blank |
| R10 | GET /health | ✓ implemented | `main.go:37-39` returns `{"status":"ok"}`; `main_test.go:28` |
| R11 | README with setup/run | ✓ implemented | `README.md` — run (`go run .`), test, env vars, endpoints, curl example |
| R12 | ≥3 unit/integration tests | ✓ implemented | 4 tests in `main_test.go`; `test_coverage=0.768 > 0` |

## Build & Test

Not re-run — stored mechanical scores were read from `scores.json` (see CLAUDE.md: do not re-run the toolchain when scores exist):

```text
scores.json:
  test_coverage = 0.768   (build + all tests passed; tests executed)
  defect_rate   = 1.0      (build + test succeeded)
  code_quality  = 1.0      (lint clean)
  maintainability = 0.851
  idiomatic     = 0.87
  token_efficiency = 0.076
```

Skip scan (`grep t.Skip`): 0 skipped tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 380 (main.go 168, store.go 107, main_test.go 105) |
| Files | 14 (incl. logs, go.mod/sum, .gitignore) |
| Dependencies (go.sum lines) | 20 |
| Tests total | 4 functions |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (scores read, not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no defects:

1. [info] Input validation exceeds spec — negative year rejected, whitespace trimmed (`main.go:73-81`)
2. [info] POST returns a `Location` header on 201 (`main.go:106`)
3. [info] PUT full-replace semantics not spelled out in README (`store.go:88`, `README.md`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-78-sonnet55-isolation/rest-api-crud/runs/effort=default_language=go_model=claude-sonnet-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores (build/test/lint)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" # skip count (0)
grep -rE "^func Test" *_test.go                    # test inventory (4)
wc -l main.go store.go main_test.go                # LOC
# To independently rebuild (optional, not required — scores already stored):
# go test ./...
```
