# Evaluation: language=python_model=sonnet_tooling=none · rep 3

## Summary

- **Factors:** language=python, model=sonnet, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — test_coverage=0.97 from retort.db
- **Lint:** code_quality=0.62 from retort.db — 3 warnings
- **Architecture:** summary skill unavailable
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `app.py:57-81` `create_book()` accepts all four fields, returns 201; `test_app.py:31` `test_create_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:84-94` `list_books()` returns full collection; `test_app.py:54` `test_list_books` |
| R3 | GET /books supports an ?author= filter | ✓ implemented | `app.py:86-91` filters with `LIKE ?` on author param; `test_app.py:64` `test_list_books_filter_by_author` |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `app.py:97-103` `get_book()` returns book or 404; `test_app.py:75` `test_get_book`, `test_app.py:84` `test_get_book_not_found` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:106-133` `update_book()` merges fields, validates, returns updated; `test_app.py:89` `test_update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:136-144` `delete_book()` removes book, returns 204; `test_app.py:106` `test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1` imports `sqlite3`; `app.py:10-15` `get_db()` connects to SQLite file; `app.py:26-39` `init_db()` creates table |
| R8 | Returns JSON responses with appropriate HTTP status codes | ✓ implemented | All routes use `jsonify()`; codes: 201 create, 200 get/list/update, 204 delete, 400 validation, 404 not found |
| R9 | Input validation: title and author are required | ✓ implemented | `app.py:64-68` validates on create; `app.py:122-125` validates on update; `test_app.py:42` `test_create_book_missing_title`, `test_app.py:48` `test_create_book_missing_author` |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:52-54` returns `{"status": "ok"}`; `test_app.py:25` `test_health` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` documents pip install, python app.py, and all endpoints with curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 12 test functions in `test_app.py` covering all CRUD operations, validation, and error cases |

## Build & Test

```text
Build/test scores from retort.db (not re-run):
  test_coverage    = 0.97
  code_quality     = 0.622
  defect_rate      = 0.307
  maintainability  = 1.0
  idiomatic        = 0.73
  token_efficiency = 0.5
```

```text
12 test functions in test_app.py:
  test_health, test_create_book, test_create_book_missing_title,
  test_create_book_missing_author, test_list_books, test_list_books_filter_by_author,
  test_get_book, test_get_book_not_found, test_update_book, test_update_book_not_found,
  test_delete_book, test_delete_book_not_found
Skipped: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 268 (149 app.py + 119 test_app.py) |
| Files | 6 |
| Dependencies | 2 (flask, pytest) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (scores from DB) |

## Findings

Top 4 by severity (full list in `findings.jsonl`):

1. [medium] SQL LIKE filter vulnerable to wildcard injection — `app.py:90`
2. [low] DATABASE module global mutated by test fixture — `test_app.py:15`
3. [low] init_db() not called on app startup via import — `app.py:147-149`
4. [info] No pagination on GET /books — `app.py:84-94`

## Reproduce

```bash
cd experiment-1/runs/language=python_model=sonnet_tooling=none/rep3
cat stack.json
cat scores.json 2>/dev/null || sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'$.language')='python' AND json_extract(er.run_config_json,'$.model')='sonnet' AND json_extract(er.run_config_json,'$.tooling')='none' AND er.replicate=3 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
grep -rE "pytest.skip|@pytest.mark.skip|xfail" --include="*.py" . | wc -l
grep -c "^def test_" test_app.py
wc -l *.py
```
