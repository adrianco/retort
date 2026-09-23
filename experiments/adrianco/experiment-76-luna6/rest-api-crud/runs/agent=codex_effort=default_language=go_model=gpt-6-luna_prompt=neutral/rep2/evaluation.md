# Evaluation: agent=codex effort=default language=go model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — `test_coverage=0.588`, `defect_rate=1.0` from `scores.json` (build+test succeeded)
- **Lint:** pass — `code_quality=0.9556` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

Requirements are the pinned checklist from `REQUIREMENTS.json` (12 items, constant across all runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:createBook` INSERT; `TestCreateListAndFilterBooks` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:listBooks`; `TestCreateListAndFilterBooks` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:listBooks` `WHERE author = ?`; filter asserted in `TestCreateListAndFilterBooks` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `main.go:getBook` → `sql.ErrNoRows`→404; `TestValidationAndNotFound` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:updateBook` UPDATE, 404 on 0 rows; `TestUpdateAndDeleteBook` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:deleteBook` DELETE→204, 404 on 0 rows; `TestUpdateAndDeleteBook` |
| R7 | Data stored in SQLite | ✓ implemented | `mattn/go-sqlite3`; `CREATE TABLE books` in `NewAPI` |
| R8 | JSON responses + status codes | ✓ implemented | `writeJSON`/`writeError`; 201/200/204/400/404/405 used |
| R9 | Validation: title & author required | ✓ implemented | `main.go:validateBook` (trim+non-empty); `TestValidationAndNotFound` (400) |
| R10 | GET /health | ✓ implemented | `main.go:ServeHTTP` `/health`→200 `{"status":"ok"}`; `TestHealthCheck` |
| R11 | README with setup/run | ✓ implemented | `README.md` (Run, Endpoints, Test sections) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 4 tests in `main_test.go`; `test_coverage=0.588 > 0` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.588   # build + tests executed and passed (Go coverage 58.8%)
defect_rate   = 1.0      # build+test succeeded
code_quality  = 0.9556
maintainability = 0.9373
idiomatic     = 0.7
```

```text
go test ./...    # 4 tests, 0 skipped (grep t.Skip → 0)
TestCreateListAndFilterBooks, TestValidationAndNotFound, TestUpdateAndDeleteBook, TestHealthCheck
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.go) | 240 |
| Lines of code (main_test.go) | 105 |
| Files (excl. .git) | 12 |
| Dependencies (direct) | 1 (`github.com/mattn/go-sqlite3`) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Coverage | 58.8% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Robust request handling beyond spec — `MaxBytesReader` + `DisallowUnknownFields`, trailing-JSON rejection, and `405`+`Allow` for wrong methods.

No requirement, build, test, or skipped-test defects were found.

## Reproduce

```bash
cd "experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=go_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json                       # stored build/test/quality scores
grep -rE "t\.Skip\(|t\.Skipf\(" . --include="*.go" | wc -l   # 0 skips
grep -cE "^func Test" main_test.go    # 4 tests
# (build/test not re-run: scores.json present, per evaluate-run skill)
```
