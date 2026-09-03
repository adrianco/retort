# Evaluation: dwq4 · rep 4

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ, agent=hermes-0205, prompt=neutral, stack=dwq4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — from `defect_rate=1.0`, `test_coverage=0.94` in scores.json
- **Build:** pass (Flask app imports; tests ran) — from scores.json
- **Lint:** n/a — `code_quality=0.79` from scores.json
- **Architecture:** single-file Flask + sqlite3 app (`app.py`) with a unittest suite (`test_app.py`); run-summary skill not available, summarized inline
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:37` create_book, INSERT at :55, 201 at :67 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:72` get_books, returns list at :88 |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:80-81` LIKE filter; test `test_filter_books_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:90` get_book, 404 at :102 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:106` update_book, UPDATE at :132, 404 at :129 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:148` delete_book, DELETE at :163 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:10` init_db, sqlite3 connect at :27 |
| R8 | JSON responses + correct status codes | ✓ implemented | jsonify + 201/200/404/400/500 throughout `app.py` |
| R9 | Validation: title and author required | ✓ implemented | `app.py:43` returns 400; test `test_create_book_missing_required_fields` |
| R10 | GET /health health check | ✓ implemented | `app.py:32` health_check returns 200; test `test_health_check` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` setup + run + test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 11 tests in `test_app.py` (`test_coverage=0.94`) |

## Build & Test

```text
python -m pytest test_app.py -v
Scores read from scores.json (not re-run): test_coverage=0.94, defect_rate=1.0
=> build + all tests passed, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py, non-blank) | 136 |
| Lines of code (test_app.py, non-blank) | 200 |
| Files (source) | 4 (app.py, test_app.py, requirements.txt, README.md) |
| Dependencies | 1 (Flask==2.3.3) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| code_quality | 0.79 |
| maintainability | 0.99 |
| idiomatic | 0.40 |

## Findings

Full list in `findings.jsonl`:

1. [low] README says port 5000 but app runs on 5001 (`README.md:35` vs `app.py:173`)
2. [info] `?author=` filter uses LIKE '%..%' substring match, not exact (`app.py:81`)

No high/critical findings. This run is a clean pass: all 12 pinned requirements implemented, tests pass with no skips.

## Reproduce

```bash
cd "<run_dir>"
cat scores.json          # test_coverage=0.94, defect_rate=1.0
python -m pytest test_app.py -v
```
