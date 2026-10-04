# Evaluation: rest-api-crud (effort=medium, go, claude-opus-5-5, prompt=neutral) · rep 1

## Summary

- **Factors:** language=go, model=claude-opus-5-5, prompt=neutral, effort=medium
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 test functions (many table-driven subtests), 0 skipped — all effective
- **Build:** pass (test_coverage=0.772 from scores.json ⇒ build + tests ran and passed)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Checklist pinned by `REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `handlers.go:80 handleCreate` → `store.go:68 Create`; test `handlers_test.go:67 TestCreateAndGet` |
| R2 | GET /books lists all | ✓ implemented | `handlers.go:94 handleList` → `store.go:85 List`; test `handlers_test.go:154` |
| R3 | GET /books ?author= filter | ✓ implemented | `handlers.go:95` + `store.go:88-91` (case-insensitive); test `handlers_test.go:178,188` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `handlers.go:104 handleGet` → `store.go:113 Get` maps `ErrNotFound`→404; test `handlers_test.go:290` |
| R5 | PUT /books/{id} updates | ✓ implemented | `handlers.go:117 handleUpdate` → `store.go:125 Update`; test `handlers_test.go:205 TestUpdate` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `handlers.go:134 handleDelete` → `store.go:144 Delete`; test `handlers_test.go:263 TestDelete` |
| R7 | Data stored in SQLite | ✓ implemented | `store.go:8 modernc.org/sqlite`, schema `store.go:28`; test `handlers_test.go:330 TestPersistsAcrossReopen` |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON handlers.go:202`; 201/200/204/400/404/405/413 used throughout; tested |
| R9 | Validation: title & author required | ✓ implemented | `handlers.go:49 validate()` rejects blank; test `handlers_test.go:94 TestCreateValidation` |
| R10 | GET /health | ✓ implemented | `handlers.go:71 handleHealth` (pings DB); test `handlers_test.go:55 TestHealth` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, env vars, API, examples |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 11 test functions; test_coverage=0.772 > 0 |

## Build & Test

Not re-run — scores read from `scores.json` (inline gate output for this run):

```text
scores.json: {"code_quality": 1.0, "token_efficiency": 0.0916, "test_coverage": 0.772,
              "defect_rate": 1.0, "maintainability": 0.8615, "idiomatic": 0.87}
```

- `test_coverage=0.772` ⇒ `go test` built and all tests passed (0.772 is line coverage, non-zero = tests executed).
- `defect_rate=1.0` ⇒ build + test succeeded.
- `code_quality=1.0` ⇒ lint/quality clean.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 456 (main 59 + handlers 240 + store 157) |
| Test lines | 353 |
| Files (tracked source) | 6 (3 src + 1 test + go.mod + go.sum + README) |
| Dependencies (direct) | 1 (`modernc.org/sqlite`); 50 go.sum entries |
| Test functions | 11 |
| Tests skipped | 0 |
| Skip ratio | 0% |
| Coverage | 77.2% |

## Findings

All 3 findings are `info`-level enhancements beyond spec (no deductions):

1. [info] Graceful shutdown + server read/write/idle timeouts (`main.go:24-51`)
2. [info] SQL-injection and 1 MiB body-size hardening, with tests (`handlers_test.go:199,322`)
3. [info] JSON-normalized 404/405 responses via `jsonErrors` wrapper (`handlers.go:212-240`)

## Reproduce

```bash
cd experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=medium_language=go_model=claude-opus-5-5_prompt=neutral/rep1
cat scores.json                                   # build/test/lint scores (not re-run)
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" handlers_test.go            # 11 test functions
# Optional live check:
go test ./...
```
