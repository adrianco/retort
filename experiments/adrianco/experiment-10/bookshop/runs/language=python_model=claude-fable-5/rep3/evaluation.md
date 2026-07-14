# Evaluation: language=python_model=claude-fable-5 · rep 3

## Summary

- **Factors:** language=python, model=claude-fable-5, agent=unknown, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — test_coverage=0.95, defect_rate=1.0 from scores.json
- **Lint:** partial pass — code_quality=0.667 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `app.py:88-105` `create_book()` accepts all four fields, persists via INSERT |
| R2 | GET /books lists all books | ✓ implemented | `app.py:107-117` `list_books()` returns full collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:109-114` filters by author query param; test at `test_app.py:60` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `app.py:119-124` `get_book()` returns one book, 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:126-150` `update_book()` with partial update support |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:152-158` `delete_book()` returns 204, 404 if absent |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:3` imports sqlite3; `app.py:9-16` CREATE TABLE schema; `app.py:24` connects |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | All routes use `jsonify()`; 201/200/204/400/404 codes correct |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:48-82` `validate_payload()` rejects missing/blank title/author with 400 |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:84-86` returns `{"status": "ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` covers setup, run, API docs, examples, and test instructions |
| R12 | At least 3 unit/integration tests | ✓ implemented | 10 test functions in `test_app.py` |

## Build & Test

```text
Build/test scores from scores.json (retort scorers already ran them):
  test_coverage:   0.95
  defect_rate:     1.0  (build+test succeeded)
  code_quality:    0.667
  maintainability: 0.274
  idiomatic:       0.71
  token_efficiency: 1.0
```

```text
Test suite: 10 test functions in test_app.py
  test_health
  test_create_book
  test_create_book_requires_title_and_author
  test_create_book_rejects_invalid_year
  test_list_books_and_author_filter
  test_get_book
  test_get_missing_book_returns_404
  test_update_book
  test_update_book_validation_and_missing
  test_delete_book
Skipped: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 290 (173 app + 117 test) |
| Files | 9 |
| Dependencies | 2 (flask, pytest) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | (from stored scores) |

## Findings

Top 3 by severity (full list in `findings.jsonl`):

1. [medium] code_quality score 0.667 indicates lint warnings
2. [low] Low maintainability score (0.274) — single-file architecture
3. [low] Dynamic SQL column construction in update_book — safe but fragile pattern

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=python_model=claude-fable-5/rep3
cat scores.json
cat stack.json
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l
grep -c "^def test_" test_app.py
find . -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" | xargs wc -l
```
