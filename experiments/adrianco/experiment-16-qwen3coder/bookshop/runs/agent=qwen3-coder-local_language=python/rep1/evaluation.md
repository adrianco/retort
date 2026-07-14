# Evaluation: agent=qwen3-coder-local language=python · rep 1

## Summary

- **Factors:** language=python, agent=qwen3-coder-local, framework=unknown (Flask + Flask-SQLAlchemy)
- **Status:** ok (all functional requirements implemented) — but the grading harness scores `test_coverage=0.05` because the real test suite is not discovered; see Findings.
- **Requirements:** 11/12 implemented, 1 partial (R12), 0 missing
- **Tests:** harness = 0 passed / 2 failed / 0 skipped (2 effective); real suite `tests.py` = 11 passed when run explicitly
- **Build:** pass — `defect_rate=1.0` from scores.json (ruff + py_compile clean)
- **Lint:** pass — `code_quality=0.83` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 2 high, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:48 create_book` — persists all four fields |
| R2 | GET /books lists all books | ✓ implemented | `app.py:73 get_books` — `Book.query.all()` |
| R3 | GET /books supports `?author=` filter | ✓ implemented | `app.py:75-78` — `filter_by(author=...)` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:85 get_book` — `get_or_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:91 update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:118 delete_book` |
| R7 | Data stored in SQLite / embedded DB | ✓ implemented | `app.py:11` SQLite URI; `books.db` present |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `jsonify(...), 201/200/404/400/500` throughout |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:53` rejects missing title/author with 400 |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:43 health_check` -> `{"status":"healthy"}` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — setup, run, endpoints (minor: wrong port, see D1) |
| R12 | At least 3 unit/integration tests | ~ partial | `tests.py` has 11 passing tests, but pytest default discovery doesn't collect `tests.py`; harness runs only `test_api.py` (fails 0/2). `test_coverage=0.05` |

## Build & Test

```text
# Harness command (scored): python -m pytest --cov=. --cov-report=term -q
Name          Stmts   Miss  Cover
---------------------------------
app.py           80     80     0%
test_api.py      52     40    23%
tests.py         99     99     0%
---------------------------------
TOTAL           231    219     5%
FAILED test_api.py::test_health           - ConnectionError (localhost:5001 refused)
FAILED test_api.py::test_books_operations - ConnectionError (localhost:5001 refused)
2 failed in 0.34s
```

```text
# Real suite run explicitly: python -m pytest tests.py -q
...........
11 passed in 0.97s
```

The code is functionally complete and correct; the low `test_coverage` is a
**test-harness discovery mismatch**, not a code defect:
- `tests.py` (the good 11-test unittest suite) is invisible to pytest's default
  discovery (needs `test_*.py` / `*_test.py`).
- `test_api.py` (the only collected file) is a live-server smoke script that
  requires `python app.py` running on :5001, so it fails headless.

`defect_rate=1.0` and `code_quality=0.83` confirm the source itself builds and
lints clean.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py, source only) | 131 (109 non-blank) |
| Files (excl. logs/artifacts) | 11 |
| Dependencies | 2 (Flask, Flask-SQLAlchemy) |
| Tests total (real suite `tests.py`) | 11 |
| Tests effective (harness-collected) | 2 (both failing) |
| Skip ratio | 0% |
| Build | pass (defect_rate=1.0) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [high] R12 — Real suite `tests.py` not collected by pytest default discovery; harness measures 5% coverage (app.py 0%).
2. [high] T1 — `test_api.py` fails 0/2 under the harness (ConnectionError, needs a live server on :5001).
3. [low] D1 — README documents port 5000 but `app.py:131` listens on 5001.

## Reproduce

```bash
cd experiment-16-qwen3coder/bookshop/runs/agent=qwen3-coder-local_language=python/rep1
# Stored mechanical scores (source of truth — do not re-run the toolchain):
cat scores.json   # test_coverage=0.05, defect_rate=1.0, code_quality=0.83

# Demonstrate the discovery mismatch (in a temp copy, never in run_dir):
python -m pytest --cov=. --cov-report=term -q   # harness view: 2 failed, TOTAL 5%
python -m pytest tests.py -q                     # real suite:  11 passed
```
