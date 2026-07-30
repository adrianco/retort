# Evaluation: agent=codex effort=high language=go model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=go, model=gpt-5.6-terra, agent=codex, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — `defect_rate=1.0` from retort.db (build+test succeeded)
- **Lint:** pass — `code_quality=0.956` from retort.db
- **Architecture:** single-package `net/http` service; `run-summary` skill unavailable (not in this session)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Denominator is the pinned 12-item `REQUIREMENTS.json` (constant across all runs of this task).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.go:83` createBook, INSERT of 4 fields; test `TestCreateAndGetBook` |
| R2 | GET /books lists all books | ✓ implemented | `main.go:101` listBooks returns collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.go:105-108` WHERE author=?; test `TestListBooksFiltersByAuthor` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `main.go:132` getBook, 404 at `main.go:139` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.go:149` updateBook, UPDATE + RowsAffected 404 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.go:175` deleteBook, 204 at `main.go:194` |
| R7 | Data stored in SQLite | ✓ implemented | `main.go:15` go-sqlite3; `main.go:39` OpenDatabase creates schema |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `main.go:234` writeJSON; 201/200/404/400/204 used across handlers |
| R9 | Input validation: title and author required | ✓ implemented | `main.go:216-221` rejects empty title/author with 400; test `TestUpdateDeleteAndValidation` |
| R10 | GET /health health-check | ✓ implemented | `main.go:75` health pings DB; test `TestHealth` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md:1-38` run/endpoints/test sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 `Test*` funcs in `main_test.go`; `test_coverage>0` |

Prompt factor (`neutral`): only asks for "whatever approach you judge best" plus tests — no additional checkable constraints beyond R12. Satisfied.

## Build & Test

Not re-run — mechanical scores read from `retort.db` / `scores.json` per skill policy.

```text
defect_rate     = 1.0    (build + all tests passed)
test_coverage   = 0.575 (scores.json) / 0.617 (retort.db) — statement coverage; tests executed and passed
code_quality    = 0.956
maintainability = 0.955
idiomatic       = 0.70 / 0.75
4 test functions, 0 skips (grep t.Skip -> 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (main.go, source) | 266 |
| Lines of code (main_test.go) | 131 |
| Files (excl .git) | 12 (incl logs/caches; 5 source: main.go, main_test.go, go.mod, go.sum, README.md) |
| Dependencies (go.sum lines) | 2 (go-sqlite3) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run); run wall-clock 149.8s, 316k tokens, $0.234 |

## Findings

All findings are informational (no defects). Full list in `findings.jsonl`:

1. [info] Robust request-body handling beyond spec (MaxBytesReader, DisallowUnknownFields) — `main.go:203-223`
2. [info] Handler/DB separation enables in-memory testing — `main.go:63`, `main_test.go:15`
3. [info] PUT full-replace semantics not documented as such — `main.go:158`, `README.md:31`

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=high_language=go_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                       # mechanical scores (build/test/quality)
grep -rE "^func Test" *.go            # 4 test functions
grep -rE "t\.Skip\(|t\.Skipf\(" .     # 0 skips
# build/test intentionally NOT re-run — scores read from retort.db per evaluate-run skill
```
