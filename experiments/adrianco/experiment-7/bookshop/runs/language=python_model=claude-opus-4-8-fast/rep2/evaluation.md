# Evaluation: language=python_model=claude-opus-4-8-fast · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-4-8-fast
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=0.96, defect_rate=1.0 from scores.json
- **Lint:** code_quality=0.67 from scores.json — lint warnings present
- **Architecture:** summary skill unavailable
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 1 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|-----|-----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `app.py:109-122` — `create_book` route accepts all four fields, inserts into SQLite, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:124-134` — `list_books` route returns full collection with 200 |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:127-131` — filters by `request.args.get("author")` with parameterized query |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `app.py:136-141` — `get_book` route with 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:144-162` — `update_book` with partial validation and 404 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:164-172` — `delete_book` with 204 response and 404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:6,14-20` — `import sqlite3`, `get_db()` opens SQLite connection; `books.db` file present |
| R8 | Returns JSON with appropriate HTTP status codes | ✓ implemented | All routes use `jsonify()` with correct codes: 201 (create), 200 (get/list/update), 204 (delete), 400 (validation), 404 (not found) |
| R9 | Input validation: title and author are required | ✓ implemented | `app.py:55-90` — `validate_book` rejects missing/empty title or author with 400; tested in `test_app.py:45-55` |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:105-107` — returns `{"status": "ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 85 lines covering setup, run, endpoints, examples, status codes, tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` — 7 test functions: health, create, validation, get, list+filter, update, delete |

## Build & Test

```text
Build/test scores read from scores.json (not re-run per skill policy):
  test_coverage: 0.96
  defect_rate:   1.0  (build + tests succeeded)
  code_quality:  0.67
```

```text
Test functions in test_app.py:
  test_health
  test_create_book
  test_create_book_requires_title_and_author
  test_get_book
  test_list_books_and_author_filter
  test_update_book
  test_delete_book
  ----
  7 tests, 0 skipped, 0 xfail
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 281 (182 app + 99 test) |
| Files (non-artifact) | 5 (app.py, test_app.py, README.md, requirements.txt, TASK.md) |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [medium] code_quality score 0.67 — lint warnings present
2. [medium] maintainability score 0.27 — single-file architecture
3. [low] test_coverage 0.96 — not all code paths exercised

## Reproduce

```bash
cd experiment-7/bookshop/runs/language=python_model=claude-opus-4-8-fast/rep2
cat scores.json
cat stack.json
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py"
find . -name "*.py" -not -path "*/venv/*" -not -path "*/__pycache__/*" -exec wc -l {} +
```
