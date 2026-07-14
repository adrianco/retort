# Evaluation: language=python_model=claude-opus-4-8-fast · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-4-8-fast
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — test_coverage=0.98, defect_rate=1.0 from scores.json
- **Lint:** pass — code_quality=1.0 from scores.json
- **Architecture:** summary skill unavailable
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|-----|-----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `main.py:54` create_book route, `db.py:55` create_book, test: `test_create_and_get_book` |
| R2 | GET /books lists all books | ✓ implemented | `main.py:58` list_books route, `db.py:69` list_books, test: `test_list_and_filter_by_author` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.py:60` author Query param, `db.py:70-71` WHERE clause, test: `test_list_and_filter_by_author` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `main.py:65` get_book route with 404, tests: `test_create_and_get_book`, `test_get_missing_book_returns_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.py:72` update_book route, tests: `test_update_book`, `test_update_missing_book_returns_404` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.py:81` delete_book route with 204, test: `test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `db.py` uses `sqlite3` module, `books.db` file, schema at `db.py:20-29` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 create, 200 get/list/update, 204 delete, 404 not found, 422 validation |
| R9 | Input validation: title and author required | ✓ implemented | `main.py:27-31` field_validator rejects blank/missing, test: `test_create_requires_title_and_author` |
| R10 | GET /health health-check endpoint | ✓ implemented | `main.py:50-52` returns `{"status": "ok"}`, test: `test_health` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` covers setup (venv + pip), run (uvicorn), API table, example curls |
| R12 | At least 3 unit/integration tests | ✓ implemented | 8 tests in `test_main.py` covering all endpoints + error paths |

## Build & Test

```text
Build/test scores read from scores.json (not re-run):
  test_coverage  = 0.98
  defect_rate    = 1.0
  code_quality   = 1.0
  maintainability = 0.2659
  idiomatic      = 0.68
  token_efficiency = 1.0
```

```text
8 tests in test_main.py:
  test_health
  test_create_and_get_book
  test_create_requires_title_and_author
  test_list_and_filter_by_author
  test_update_book
  test_update_missing_book_returns_404
  test_delete_book
  test_get_missing_book_returns_404
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 303 (3 Python files) |
| Files | 9 (excluding build artifacts) |
| Dependencies | 4 (fastapi, uvicorn, httpx, pytest) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | N/A (scores from scores.json) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] Input validation returns 422 instead of 400 — FastAPI/Pydantic convention
2. [info] Maintainability score is low (0.27) — likely missing type annotations/docstrings in db.py

## Reproduce

```bash
cd experiment-7/bookshop/runs/language=python_model=claude-opus-4-8-fast/rep1
cat scores.json
cat TASK.md
cat stack.json
grep -rE "pytest.skip|@pytest.mark.skip|xfail" . --include="*.py"
find . -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" | xargs wc -l
```
