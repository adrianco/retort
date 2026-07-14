# Evaluation: language=python_model=claude-opus-4-8_tooling=none · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-4-8, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** code_quality=0.789 from retort.db
- **Architecture:** summary skill not invoked (single-file app)
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✓ implemented | `app.py:145-168` do_POST inserts title, author, year, isbn; returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:115-129` returns all books ordered by id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:117-124` parses query param, filters with SQL WHERE clause |
| R4 | GET /books/{id} returns single book | ✓ implemented | `app.py:132-143` matches `/books/<id>`, returns 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:170-201` do_PUT validates, updates, returns 200 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:203-214` do_DELETE removes row, returns 204 or 404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:9,17-34` uses sqlite3, creates books table with AUTOINCREMENT id |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `app.py:81-88` _send sets Content-Type: application/json; 201/200/204/400/404 used correctly |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:47-73` _validate rejects missing/empty title or author with 400 |
| R10 | GET /health endpoint | ✓ implemented | `app.py:111-113` returns `{"status": "ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents Python 3.7+ requirement, run/test commands, API reference |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` has 7 integration tests exercising all endpoints over real HTTP |

## Build & Test

```text
Build/test scores from retort.db (not re-run):
  test_coverage = 1.0  (build + all tests passed)
  code_quality  = 0.789
  defect_rate   = 1.0  (no defects)
```

```text
Tests (7 methods in test_app.py):
  test_health
  test_create_and_get_book
  test_create_requires_title_and_author
  test_list_and_author_filter
  test_update_book
  test_delete_book
  test_get_missing_book_returns_404
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 368 (239 app.py + 129 test_app.py) |
| Files | 5 (app.py, test_app.py, README.md, stack.json, TASK.md) |
| Dependencies | 0 (stdlib only) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Inline import of `urllib.parse.unquote` inside `do_GET` (app.py:119)

## Reproduce

```bash
cd experiment-6/runs/language=python_model=claude-opus-4-8_tooling=none/rep1
python3 -m unittest test_app -v
```
