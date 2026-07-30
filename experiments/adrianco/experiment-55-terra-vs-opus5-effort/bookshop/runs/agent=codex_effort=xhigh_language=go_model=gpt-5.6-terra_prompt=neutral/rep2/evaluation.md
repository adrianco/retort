# Evaluation: agent=codex effort=xhigh language=go model=gpt-5.6-terra prompt=neutral · rep 2

## Summary

- **Factors:** language=go, model=gpt-5.6-terra, agent=codex, effort=xhigh, prompt=neutral, framework=unknown (net/http stdlib)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=1.0 from scores.json
- **Coverage:** 61.1% (test_coverage=0.611 from scores.json)
- **Architecture:** run-summary skill unavailable; net/http stdlib router (`main.go`) + persistence/HTTP helpers (`book.go`) + tests (`main_test.go`)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `main.go:138` createBook, INSERT with title/author/year/isbn → 201 |
| R2 | GET /books lists all | ✓ implemented | `main.go:160` listBooks, SELECT ORDER BY id → 200 |
| R3 | GET /books ?author= filter | ✓ implemented | `main.go:165` adds `WHERE author = ?`; test at `main_test.go:62` |
| R4 | GET /books/{id} single | ✓ implemented | `main.go:194` getBook; `sql.ErrNoRows`→404 at `main.go:196` |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.go:207` updateBook; RowsAffected==0→404 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.go:233` deleteBook → 204; 404 if absent |
| R7 | SQLite / embedded DB | ✓ implemented | `main.go:14,49` modernc.org/sqlite, `OpenDatabase` creates schema |
| R8 | JSON + proper status codes | ✓ implemented | `book.go:71` writeJSON; 201/200/204/400/404/405/503 used throughout |
| R9 | Validation: title+author required | ✓ implemented | `book.go:62-67` rejects empty title/author→400; test `main_test.go:109` |
| R10 | GET /health | ✓ implemented | `main.go:96` health, pings DB, returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — run, env vars, API table, curl examples, test cmd |
| R12 | ≥3 unit/integration tests | ✓ implemented | 4 tests in `main_test.go`; 0 skips |

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
test_coverage = 0.611   (build + tests passed; 61.1% statement coverage)
defect_rate   = 1.0      (build + test succeeded)
code_quality  = 1.0      (lint clean)
idiomatic     = 0.87
maintainability = 0.735
```

Tests present (`main_test.go`): TestCreateAndGetBook, TestListCanFilterByAuthor,
TestUpdateThenDeleteBook, TestValidationAndHealth — all exercise the API via
`httptest` against an in-memory SQLite handler.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 466 (main.go+book.go+main_test.go) |
| Files (excl .gocache/.git) | 14 |
| Direct dependencies | 1 (modernc.org/sqlite) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Coverage | 61.1% |

## Findings

Full list in `findings.jsonl`:

1. [low] Error/edge paths untested (coverage 61.1%) — 404, malformed JSON, 405 not exercised
2. [info] ?author= filter is exact-match only (spec-satisfying)
3. [info] PUT is a full replacement, not partial (spec-satisfying)

No critical/high/medium findings. This is a complete, idiomatic, passing implementation.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=xhigh_language=go_model=gpt-5.6-terra_prompt=neutral/rep2"
cat scores.json                 # stored mechanical scores (no re-run)
go test ./...                   # optional: reproduce test pass locally
go test -cover ./...            # optional: reproduce 61.1% coverage
```
