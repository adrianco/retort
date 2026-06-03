# Evaluation: language=python_model=claude-opus-4-8_tooling=beads · rep 3

## Summary

- **Factors:** language=python, model=claude-opus-4-8, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass — test_coverage=0.94, defect_rate=1.0 from retort.db
- **Lint:** pass — code_quality=0.8667 from retort.db
- **Architecture:** summary skill not invoked (single-file app, straightforward)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `app.py:117-138` `create_book()` — inserts all 4 fields; test `test_create_book` at `test_app.py:51` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:140-150` `list_books()` — returns full collection; test `test_list_books_and_author_filter` at `test_app.py:88` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:142-148` checks `request.args.get("author")` and filters via SQL WHERE; test at `test_app.py:97-100` |
| R4 | GET /books/{id} returns single book | ✓ implemented | `app.py:152-159` `get_book()` with 404 handling; tests `test_get_book` and `test_get_missing_book_returns_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:162-183` `update_book()` with partial update support; tests `test_update_book` and `test_update_missing_book_returns_404` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:185-195` `delete_book()` returns 204; tests `test_delete_book` and `test_delete_missing_book_returns_404` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:8` imports `sqlite3`; `app.py:30-43` `init_db()` creates `books` table with `CREATE TABLE IF NOT EXISTS` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | All routes use `jsonify()` and return correct codes: 201 (create), 200 (read/update), 204 (delete), 400 (validation), 404 (not found) |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:58-98` `validate_payload()` rejects missing/blank title/author with 400; tests `test_create_book_requires_title_and_author` at `test_app.py:61` and `test_create_book_rejects_blank_title` at `test_app.py:71` |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:113-115` returns `{"status": "ok"}` with 200; test `test_health` at `test_app.py:45` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` (93 lines) covers setup (venv, pip install), running (two options), API table, examples, and test command |
| R12 | At least 3 unit/integration tests | ✓ implemented | 11 test functions in `test_app.py`; test_coverage=0.94 from retort.db confirms tests executed and passed |

## Build & Test

```text
Build/test scores from retort.db (not re-run per skill policy):
  test_coverage  = 0.94
  code_quality   = 0.8667
  defect_rate    = 1.0   (build + test succeeded)
  idiomatic      = 0.68
  maintainability = 0.2738
  token_efficiency = 1.0
```

```text
11 test functions in test_app.py:
  test_health
  test_create_book
  test_create_book_requires_title_and_author
  test_create_book_rejects_blank_title
  test_get_book
  test_get_missing_book_returns_404
  test_list_books_and_author_filter
  test_update_book
  test_update_missing_book_returns_404
  test_delete_book
  test_delete_missing_book_returns_404
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 331 (205 app.py + 126 test_app.py) |
| Files | 12 (excluding .venv and build artifacts) |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | scored by retort (not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [info] Code coverage at 94% — not full line coverage
2. [info] Low maintainability score (0.27) — single-file architecture

## Reproduce

```bash
cd experiment-6/runs/language=python_model=claude-opus-4-8_tooling=beads/rep3
cat stack.json
cat scores.json  # if present; otherwise query retort.db
grep -cE "^def test_" test_app.py
grep -rE "pytest.skip|@pytest.mark.skip|xfail" test_app.py app.py
```
