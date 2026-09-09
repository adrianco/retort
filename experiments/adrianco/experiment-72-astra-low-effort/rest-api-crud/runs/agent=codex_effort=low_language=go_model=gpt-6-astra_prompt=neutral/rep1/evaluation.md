# Evaluation: rest-api-crud · agent=codex_effort=low_language=go_model=gpt-6-astra_prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=gpt-6-astra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 test functions (+subtests) passed / 0 failed / 0 skipped (all effective)
- **Build:** pass — from `defect_rate=1.0` in scores.json (not re-run)
- **Lint:** pass — `code_quality=0.956` in scores.json
- **Coverage:** `test_coverage=0.76` in scores.json (tests executed and passed)
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:80,140` save() → INSERT `main.go:153`; `TestCRUD` |
| R2 | GET /books lists all | ✓ implemented | `main.go:184` list(); `TestListAndFilter` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:187-190` WHERE author=?; `TestListAndFilter` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `main.go:212` get(); 404 at `main.go:216`; `TestCRUD` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:166` UPDATE; 404 at `main.go:177`; `TestCRUD` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:225` delete(); 204/404; `TestCRUD` |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:16,29` go-sqlite3, file DB; `TestPersistence` |
| R8 | JSON + correct status codes | ✓ implemented | `respond`/`fail` `main.go:50-57`; 201/200/404/400/405/413/503 |
| R9 | Validation: title+author required | ✓ implemented | `readBook` `main.go:135`; SQL CHECK `main.go:38-39`; `TestValidation` |
| R10 | GET /health | ✓ implemented | `main.go:64-74`; `TestRoutingAndHealth` |
| R11 | README with setup/run | ✓ implemented | `README.md` — build/run, env vars, full API table |
| R12 | >= 3 tests | ✓ implemented | `main_test.go` — 5 test funcs; `test_coverage=0.76` |

Enhancements beyond spec: 1 MiB body limit (413), unknown-field & trailing-JSON
rejection, `Allow` header on 405, server read/write timeouts, SQL non-blank
CHECK constraints, SQL-injection-safe parameterized filter (tested).

## Build & Test

Not re-run — stored scores read from `scores.json` (per evaluate-run Step 2):

```text
defect_rate      = 1.0    (build + tests succeeded)
test_coverage    = 0.76   (tests executed; > 0 ⇒ test gate passed)
code_quality     = 0.956
maintainability  = 0.976
idiomatic        = 0.82
token_efficiency = 0.025
```

Skipped/disabled tests: 0 (`grep t.Skip` → 0 matches).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 402 (main.go 264 + main_test.go 138) |
| Files (source) | 5 (main.go, main_test.go, go.mod, go.sum, README.md) |
| Dependencies | 1 direct (`github.com/mattn/go-sqlite3`) |
| Tests total | 5 functions (+ table subtests) |
| Tests effective | 5 (0 skipped) |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Full list in `findings.jsonl`. No critical/high/medium/low findings.

1. [info] GET /books has no pagination (not required by spec)
2. [info] Author filter is exact and case-sensitive (not required by spec)

## Reproduce

```bash
cd "experiments/adrianco/experiment-72-astra-low-effort/rest-api-crud/runs/agent=codex_effort=low_language=go_model=gpt-6-astra_prompt=neutral/rep1"
cat scores.json          # stored build/test/quality scores (not re-run)
grep -rE "t\.Skip\(" . --include="*.go" | wc -l   # 0 skips
go test ./...            # optional: re-verify (needs Go 1.22 + CGO)
```
