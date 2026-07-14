# Evaluation: agent=hermes-local language=python prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), prompt=neutral, framework=Flask (chosen by agent)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective)
- **Build:** pass — import/collection succeeded (test_coverage=0.95, defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.79 from scores.json (one deprecation warning)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

The neutral prompt prescribes no methodology and adds no discrete checkable requirement beyond "include tests" (already R12), so there are no `P*` items.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:70` `create_book`; `test_app.py:50` `test_create_book_success` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:93` `list_books`; `test_app.py:113` `test_list_books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:97-98` `ilike` filter; `test_app.py:123` `test_list_books_filter_by_author` |
| R4 | GET /books/{id} returns single book | ✓ implemented | `app.py:102` `get_book` (404 at :106); `test_app.py:138,150` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:109` `update_book`; `test_app.py:162` `test_update_book_success` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:144` `delete_book`; `test_app.py:204` `test_delete_book_success` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:18` `sqlite:///` URI via Flask-SQLAlchemy |
| R8 | JSON responses + correct HTTP codes | ✓ implemented | `jsonify(...)` with 201/200/400/404 across all routes |
| R9 | Input validation: title & author required | ✓ implemented | `app.py:47` `_validate_book_payload`; `test_app.py:70,81` |
| R10 | GET /health health check | ✓ implemented | `app.py:66` `health`; `test_app.py:38` `test_health` |
| R11 | README.md with setup & run instructions | ✓ implemented | `README.md:37-59` Setup and Run sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 14 tests in `test_app.py`; test_coverage=0.95 |

## Build & Test

Not re-run — stored scores used (scores.json + agent log).

```text
scores.json: test_coverage=0.95, defect_rate=1.0, code_quality=0.79,
             maintainability=1.0, idiomatic=0.88
```

```text
python -m pytest test_app.py -v   (from agent log)
14 passed in 0.16s
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py) | 167 |
| Lines of code (tests: test_app.py) | 220 |
| Files (excl. __pycache__/.coverage) | 11 (3 source: app.py, test_app.py, README.md) |
| Dependencies | 3 (flask, flask-sqlalchemy, pytest — README only) |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build duration | ~0.16s (test run) |
| Agent tokens (total) | 801,414 (17,828 output, 27 API calls) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] `datetime.utcnow()` deprecated on Python 3.12+ — `app.py:32-34`
2. [low] No dependency manifest (requirements.txt / pyproject.toml) — deps only in `README.md`
3. [info] Timestamps + year int-coercion beyond spec (enhancement) — `app.py:32-34, 82-86`

No high/critical/medium findings. Clean, fully-conformant run.

## Reproduce

```bash
cd experiment-20-hermes35b-alllang/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep1
cat scores.json                       # stored mechanical scores
pip install flask flask-sqlalchemy pytest
python -m pytest test_app.py -v       # 14 passed
```
