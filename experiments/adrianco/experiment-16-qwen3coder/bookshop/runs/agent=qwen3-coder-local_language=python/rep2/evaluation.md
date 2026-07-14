# Evaluation: agent=qwen3-coder-local language=python · rep 2

## Summary

- **Factors:** language=python, agent=qwen3-coder-local, framework=unknown (Flask + Flask-SQLAlchemy in practice)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — from `test_app.py`; plus non-harness `integration_test.py` and `verify.py`
- **Build:** pass — `test_coverage=0.64`, `defect_rate=1.0` from `scores.json` (build + tests executed successfully)
- **Lint:** pass — `code_quality=0.8333` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 6 items in `findings.jsonl` (0 critical, 0 high, 3 medium, 2 low, 1 info)

## Requirements

Using pinned `bookshop/REQUIREMENTS.json` (12 fixed requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:61-83` create_book; test `test_app.py:41 test_create_book` |
| R2 | GET /books lists all | ✓ implemented | `app.py:86-95` get_books; test `test_app.py:72 test_get_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:88-91` filter_by(author); test `test_app.py:80 test_get_books_by_author` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:98-101` get_or_404; tests `test_get_book_by_id`, `test_get_nonexistent_book` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:104-127` update_book; test `test_app.py:116 test_update_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:130-140` delete_book; test `test_app.py:143 test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:15` sqlite:///books.db; `books.db` present in run dir |
| R8 | JSON responses + status codes | ✓ implemented | jsonify throughout; 201/200/404/400/500 used (`app.py:47-53, 80, 101`) |
| R9 | Validation: title & author required | ✓ implemented | `app.py:66-67` returns 400; test `test_app.py:60 test_create_book_missing_fields` |
| R10 | GET /health | ✓ implemented | `app.py:56-58` health_check; test `test_app.py:34 test_health_check` |
| R11 | README with setup/run | ✓ implemented | `README.md:28-40` Setup/Run sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 11 test methods in `test_app.py`; `test_coverage=0.64 > 0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill step 2):

```text
scores.json:
  test_coverage   = 0.64   (tests executed; 64% line coverage)
  defect_rate     = 1.0    (build + tests succeeded)
  code_quality    = 0.8333
  maintainability = 0.9339
  idiomatic       = 0.62
  token_efficiency= 0.0056
```

Skip scan (`grep pytest.skip|unittest.skip|xfail`): 0 skips found.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, incl. README) | 542 (app.py 142, test_app.py 159, integration_test.py 77, verify.py 73, README.md 91) |
| Source files | 5 (1 app + 3 test/verify + README) |
| Dependencies | 2 (flask, flask-sqlalchemy) — from README prose; no requirements.txt |
| Tests total (harness) | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build/test | pass (scores.json) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [medium] Dev server runs with `debug=True` bound to `0.0.0.0` (`app.py:143`) — Werkzeug debugger RCE exposed on all interfaces.
2. [medium] `year` is `nullable=False` but never validated → POST without `year` returns generic 500 instead of 400 (`app.py:26` vs `app.py:73`).
3. [medium] Tests operate on the app's real `books.db`; `tearDown` `drop_all()` destroys the dev DB (`test_app.py:15,31`).
4. [low] No pinned dependency manifest (`requirements.txt`/`pyproject.toml`); README only says `pip install flask flask-sqlalchemy`.
5. [low] Duplicate `isbn` (unique) returns generic 500 rather than 409 (`app.py:27,81`).

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop/runs/agent=qwen3-coder-local_language=python/rep2
cat scores.json                                        # mechanical scores (build/test/lint)
grep -rEn "pytest\.skip|unittest\.skip|xfail" . --include="*.py"   # skip scan -> none
python test_app.py                                     # optional: 11 unittest methods
```
