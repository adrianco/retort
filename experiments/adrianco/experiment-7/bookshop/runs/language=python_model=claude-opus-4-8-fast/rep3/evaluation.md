# Evaluation: language=python_model=claude-opus-4-8-fast · rep 3

## Summary

- **Factors:** language=python, model=claude-opus-4-8-fast
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — test_coverage=0.97, defect_rate=1.0 from scores.json
- **Lint:** pass — code_quality=1.0 from scores.json, 0 warnings
- **Architecture:** summary skill not invoked (single-file app, structure is self-evident)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `app.py:99-120` `create_book()` accepts all 4 fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:122-132` `list_books()` returns full collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:124-129` filters by `author` query param |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `app.py:134-139` `get_book()` with 404 for missing |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:141-166` `update_book()` with 404 for missing |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:168-175` `delete_book()` returns 204 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:7,22-39` uses `sqlite3` module, `init_db()` creates `books` table |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | All routes use `jsonify()` with codes 200/201/204/400/404 |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:66-93` `validate_book_payload()` rejects missing/empty fields with 400 |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:95-97` returns `{"status": "ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents setup, run, API endpoints, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` contains 10 test functions using pytest + Flask test client |

## Build & Test

```text
Build and test scores read from scores.json (not re-run):
  test_coverage:  0.97
  code_quality:   1.0
  defect_rate:    1.0
  maintainability: 0.27
  idiomatic:      0.68
  token_efficiency: 1.0
```

```text
Tests: 10 test functions in test_app.py
  test_health
  test_create_book
  test_create_book_requires_title_and_author
  test_get_book
  test_get_missing_book_returns_404
  test_list_books_and_author_filter
  test_update_book
  test_update_missing_book_returns_404
  test_delete_book
  test_delete_missing_book_returns_404
Skipped: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 301 (app.py: 186, test_app.py: 115) |
| Files | 12 |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Idiomatic score below average (0.68) — nested function definitions inside app factory
2. [info] Low maintainability score (0.27) despite clean code — single-file structure

## Reproduce

```bash
cd experiment-7/bookshop/runs/language=python_model=claude-opus-4-8-fast/rep3
cat scores.json
cat REQUIREMENTS.json  # (in parent experiment-7/bookshop/)
grep -rE "pytest.skip|@pytest.mark.skip|xfail" --include="*.py" | wc -l
find . -name "*.py" -not -path "*/venv/*" -not -path "*/__pycache__/*" | xargs wc -l
grep -c "^def test_" test_app.py
```
