# Evaluation: effort=default_language=python_model=claude-fable-5-1_prompt=none · rep 1

## Summary

- **Factors:** language=python, model=claude-fable-5-1, prompt=none, effort=default (agent/framework=unknown; Flask+SQLite in practice)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective) — from test_coverage=0.94, defect_rate=1.0 in scores.json
- **Build:** pass — tests executed (test_coverage=0.94 > 0)
- **Lint:** pass — code_quality=0.83 from scores.json
- **Architecture:** Flask application factory (`app/__init__.py`) + SQLite data layer (`app/db.py`) + blueprint routes (`app/routes.py`); `summary/` not generated (run-summary skipped)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app/routes.py:97 create_book`, INSERT at :107 |
| R2 | GET /books lists all books | ✓ implemented | `app/routes.py:119 list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app/routes.py:121-126` WHERE author COLLATE NOCASE |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app/routes.py:132 get_book`, 404 at :136 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app/routes.py:140 update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app/routes.py:162 delete_book`, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `app/db.py:8-17 SCHEMA`, sqlite3 connection |
| R8 | JSON responses + correct status codes | ✓ implemented | 201/200/404/400/204 across routes; JSON error handlers `app/__init__.py:27-37` |
| R9 | Validation: title and author required | ✓ implemented | `app/routes.py:35-43 _validate`; test `test_create_requires_title_and_author` |
| R10 | GET /health endpoint | ✓ implemented | `app/routes.py:85 health` returns status+db check |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` Setup/Run sections + env var table |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests/test_books.py` — 12 tests, 0 skips |

## Build & Test

Scores read from `scores.json` (not re-run per evaluate-run guidance):

```text
test_coverage = 0.94   (build + tests executed and passed)
defect_rate   = 1.0    (build+test succeeded)
code_quality  = 0.833
maintainability = 0.906
idiomatic     = 0.87
```

```text
grep def test_ tests/test_books.py -> 12 test functions
grep skip/xfail tests/ -> 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, app/ + tests/ + run.py) | ~230 |
| Files (excl. __pycache__) | 17 |
| Dependencies | 2 (flask, pytest) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] ISBN format validation beyond spec — `app/routes.py:56-68`
2. [info] JSON 404/405/500 error handlers registered — `app/__init__.py:27-37`

No requirement, build, test, or skip findings. Clean run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-65-fable51-effort/rest-api-crud/runs/effort=default_language=python_model=claude-fable-5-1_prompt=none/rep1"
cat scores.json
grep -rEc "def test_" tests/test_books.py
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py"
# optional full re-run: pip install -r requirements.txt && pytest
```
