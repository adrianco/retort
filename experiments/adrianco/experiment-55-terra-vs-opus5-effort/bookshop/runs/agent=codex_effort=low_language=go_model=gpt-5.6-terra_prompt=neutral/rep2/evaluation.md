# Evaluation: agent=codex effort=low language=go model=gpt-5.6-terra prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=gpt-5.6-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from `defect_rate=1.0` in scores.json (not re-run)
- **Lint:** pass — `code_quality=0.956` in scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

Stored scores (`scores.json`): test_coverage=0.617, defect_rate=1.0, code_quality=0.956,
maintainability=0.882, idiomatic=0.78, token_efficiency=0.052. `defect_rate=1.0` ⇒ the build
compiled and all tests passed; `test_coverage=0.617` is the measured coverage fraction. No
build/test re-run performed (per skill: read stored scores).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books create (title, author, year, isbn) | ✓ implemented | `main.go:102 createBook`, INSERT at `main.go:108` |
| R2 | GET /books list all | ✓ implemented | `main.go:117 listBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:118-123` WHERE author = ? |
| R4 | GET /books/{id} single, 404 if absent | ✓ implemented | `main.go:147 getBook`, 404 at `main.go:150` |
| R5 | PUT /books/{id} update | ✓ implemented | `main.go:160 updateBook`, UPDATE at `main.go:166` |
| R6 | DELETE /books/{id} delete | ✓ implemented | `main.go:180 deleteBook`, 404 when 0 rows |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:14` go-sqlite3, `main.go:216` sql.Open("sqlite3") |
| R8 | JSON responses + correct status codes | ✓ implemented | `writeJSON`/`writeError` at `main.go:202-209`; 201/200/204/400/404/405/500 used |
| R9 | Validation: title & author required | ✓ implemented | `main.go:95-97` decodeBook rejects empty → 400 |
| R10 | GET /health | ✓ implemented | `main.go:42-49` returns `{"status":"ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — run, endpoints, env vars, test |
| R12 | ≥3 unit/integration tests | ✓ implemented | `main_test.go` — 3 tests; test_coverage=0.617 > 0 |

## Build & Test

Not re-run — stored scores used per evaluate-run skill (§2).

```text
defect_rate = 1.0    → build compiled, all tests passed
test_coverage = 0.617 → coverage fraction (tests executed)
code_quality = 0.956  → lint/quality
```

Tests (`go test ./...`): 3 tests, 0 skips (grep `t.Skip` = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 310 (main.go 231 + main_test.go 79) |
| Files | 12 (incl. generated summary/) |
| Dependencies | 1 direct (go-sqlite3) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] `http.MaxBytesReader` called with nil ResponseWriter — `main.go:90`
2. [info] Exactly 3 tests — meets the minimum with no margin — `main_test.go`

No critical, high, or medium findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=low_language=go_model=gpt-5.6-terra_prompt=neutral/rep2"
cat scores.json          # stored mechanical scores (build/test/lint)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # skip count = 0
go test ./...            # optional: only if re-verifying (requires CGO/C compiler)
```
