# Evaluation: language=python_model=claude-opus-4-7_tooling=beads · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-4-7, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=1.0 from retort.db (build+tests succeeded)
- **Lint:** code_quality=0.789 from retort.db
- **Architecture:** summary skill not invoked (standalone evaluation)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `app.py:89-111` — `create_book()` accepts all four fields, persists to SQLite, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:113-124` — `list_books()` returns full collection with 200 |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:115-119` — filters by author query param; tested in `test_app.py:71` |
| R4 | GET /books/{id} returns single book | ✓ implemented | `app.py:126-131` — `get_book()` returns one book, 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:134-162` — `update_book()` with partial merge; tested in `test_app.py:91` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:164-172` — `delete_book()` returns 204; tested in `test_app.py:113` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:8-15` — `sqlite3.connect()`, `app.py:20-32` — `CREATE TABLE books` |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 create, 200 get/list/update, 204 delete, 400 validation, 404 not found |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:45-70` — `validate_book_payload()` rejects missing/blank title/author; tested in `test_app.py:45` |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:85-87` — returns `{"status": "ok"}` with 200; tested in `test_app.py:20` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — setup, run, test commands, endpoint table, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 7 test functions in `test_app.py`; test_coverage=1.0 from retort.db |

## Build & Test

```text
Build + test verification from retort.db stored scores:
  test_coverage = 1.0  (all tests passed, build succeeded)
  defect_rate   = 1.0  (no defects detected)
  code_quality  = 0.789
```

```text
Test functions (7 total, 0 skipped):
  test_health
  test_create_and_get_book
  test_create_book_validation
  test_list_books_and_filter_by_author
  test_update_book
  test_delete_book
  test_get_missing_book
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 312 (178 app + 134 test) |
| Files | 14 |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (stored score) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] code_quality score 0.789 suggests minor lint warnings
2. [info] PUT /books/{id} supports partial updates beyond spec (enhancement)

## Reproduce

```bash
cd experiment-6/runs/language=python_model=claude-opus-4-7_tooling=beads/rep2
cat stack.json
cat scores.json 2>/dev/null || sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='python' AND json_extract(er.run_config_json,'\$.model')='claude-opus-4-7' AND json_extract(er.run_config_json,'\$.tooling')='beads' AND er.replicate=2 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l
grep -cE "def test_" test_app.py
find . -name "*.py" -not -path "*/__pycache__/*" -exec wc -l {} +
```
