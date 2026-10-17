# Evaluation: effort=xhigh language=python model=claude-haiku-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, prompt=neutral, effort=xhigh
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned list in `REQUIREMENTS.json`)
- **Tests:** 39 passed / 0 failed / 0 skipped (39 effective)
- **Build:** pass — from `scores.json` (test_coverage=0.95, defect_rate=1.0; not re-run)
- **Lint:** pass with warnings — code_quality=0.67 from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `server.py:_create_book` → `repository.py:create` INSERT; `test_api.py:test_create_book_returns_201...` |
| R2 | GET /books lists all books | ✓ implemented | `server.py:_list_books` → `repository.py:list_books`; `test_api.py:test_list_books_returns_all...` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `repository.py:list_books` `WHERE author COLLATE NOCASE = ?`; `test_api.py:test_list_books...filters_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `server.py:_get_book`; `test_api.py:test_get_book_returns_book_or_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `server.py:_update_book` → `repository.py:update`; `test_api.py:test_update_replaces_every_field` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `server.py:_delete_book`; `test_api.py:test_delete_book_returns_204_then_404` |
| R7 | Data stored in SQLite | ✓ implemented | `repository.py` `sqlite3.connect` + schema; `test_repository.py:test_data_survives_reopening...` |
| R8 | JSON responses with correct status codes | ✓ implemented | `server.py:_send` / `_error`; 201/200/204/400/404/405/413/500 covered in `test_api.py` |
| R9 | Validation: title and author required | ✓ implemented | `validation.py:_required_text`; `test_validation.py:test_title_and_author_are_required` |
| R10 | GET /health health check | ✓ implemented | `server.py:_health` → `repository.py:ping`; `test_api.py:test_health_endpoint_reports_ok` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` Setup/Run sections with venv + CLI flags |
| R12 | At least 3 unit/integration tests | ✓ implemented | 39 test functions across 3 files; test_coverage=0.95 |

No requirements missing or partial. Enhancements beyond spec (not deductions): ISBN-10/13 and year-range validation, 1 MiB body guard (413), `Allow` header on 405, central 500 handler.

## Build & Test

Build and tests were **not re-run** — scores come from `scores.json` (written by the inline eval gate; no `retort.db` row exists yet for this cell).

```text
scores.json
test_coverage = 0.95   (build + tests ran; all pass, ~5% lines uncovered)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.667
maintainability = 0.902
idiomatic     = 0.82
token_efficiency = 0.0071
```

```text
Test inventory (static): 39 test functions
  tests/test_api.py         19
  tests/test_validation.py  12
  tests/test_repository.py   8
Skipped/xfail: 0  (grep pytest.skip|mark.skip|xfail = 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 467 (book_api/) |
| Lines of code (tests) | 451 (tests/) |
| Files (tracked, non-artifact) | 18 |
| Dependencies | 1 dev (pytest); 0 runtime |
| Tests total | 39 |
| Tests effective | 39 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] code_quality score 0.67 (below 1.0) — lint/quality scorer flagged minor issues; tests and build pass.
2. [info] ~5% of lines uncovered (test_coverage=0.95) — likely the `__main__` serve loop.
3. [info] Threaded server serialised by a single shared SQLite connection + global lock.
4. [info] Validation and error handling exceed the spec (ISBN/year, 413 guard, 405 Allow).

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=xhigh_language=python_model=claude-haiku-5-5_prompt=neutral/rep1"
cat scores.json                                          # stored build/test/lint scores (not re-run)
cat ../../../REQUIREMENTS.json                            # pinned 12-requirement checklist
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/  # skip detection (0)
grep -rcE "def test_" tests/*.py                          # test inventory
# Optional full re-run (fallback only): python -m pytest -q
```
