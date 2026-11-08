# Evaluation: agent=codex_effort=low_language=python_model=gpt-6.1-terra_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=gpt-6.1-terra, agent=codex, effort=low, prompt=neutral (framework: Flask)
- **Status:** ok (this is a self-repair run — TASK.md is a REPAIR TASK after a prior attempt failed the test gate; the repair passes)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing; prompt instructions 1/1 followed
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective) — per agent log `6 passed in 0.05s`; test_coverage=0.98 from scores.json
- **Build:** pass (derived from defect_rate=1.0 / test_coverage=0.98 in scores.json; not re-run)
- **Lint:** code_quality=0.789 (scores.json); individual warnings not re-run
- **Architecture:** summary skill not run — single-module app (`app.py`, 109 lines, Flask app factory + sqlite3)
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates book (title, author, year, isbn) | ✓ implemented | `app.py:books()` INSERT, returns 201; `test_create_get_and_persist` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:books()` GET branch; `test_create_get_and_persist` |
| R3 | ?author= filter | ✓ implemented | `app.py:books()` `WHERE author = ?`; `test_filter_update_and_delete` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app.py:book()`; 404 asserted in `test_filter_update_and_delete` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:book()` UPDATE; `test_filter_update_and_delete`, 404 in `test_validation_and_missing_books` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:book()` DELETE; `test_filter_update_and_delete` |
| R7 | SQLite storage | ✓ implemented | `sqlite3.connect(app.config["DATABASE"])`; `test_persistence_across_app_instances` |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/400/404 via `jsonify`; JSON 404/405 error handlers |
| R9 | title & author required | ✓ implemented | `validate_book()` non-empty string check; `test_validation_and_missing_books` |
| R10 | GET /health | ✓ implemented | `health()`; `test_health` |
| R11 | README with setup/run | ✓ implemented | `README.md` venv/pip/run/test instructions + curl examples |
| R12 | ≥3 tests | ✓ implemented | 6 tests in `test_app.py`, all pass |
| P1 | (neutral prompt) include tests demonstrating requirements | ✓ followed | tests cover every R1–R10 behaviour |

Enhancements beyond spec: type validation for year/isbn, SQLite int64 range check for year, JSON 404/405 handlers, `BOOKS_DATABASE` env override.

## Build & Test

```text
(not re-run — stored scores used per skill)
scores.json: test_coverage=0.98 defect_rate=1.0 code_quality=0.789 maintainability=1.0 idiomatic=0.8
agent log final check: python3 -m pytest -q -> "6 passed in 0.05s"
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 109 (app.py) + 62 (test_app.py) |
| Files | 2 source, README, requirements.txt |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

1. [low] Stored lint/quality score below 1.0 (code_quality=0.789)
2. [low] PUT is full-replace; partial updates rejected (documented in README)
3. [info] /health does not probe the database
4. [info] ISBN accepted as any string

## Reproduce

```bash
cd <run_dir>
cat scores.json
pip install -r requirements.txt && python -m pytest -q
```
