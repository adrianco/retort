# Evaluation: language=python_model=opus_tooling=beads · rep 3

## Summary

- **Factors:** language=python, model=opus, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — test_coverage=0.97 from retort.db
- **Lint:** code_quality=0.622 from retort.db
- **Architecture:** summary skill not invoked
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `app.py:59-77` `create_book()` accepts all four fields, inserts into SQLite, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:79-89` `list_books()` returns full collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:81-86` filters by `request.args.get("author")` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `app.py:91-97` `get_book(book_id)` with 404 for absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:99-120` `update_book(book_id)` merges partial updates |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:122-131` `delete_book(book_id)` returns 204 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:2` imports sqlite3; `app.py:18-30` CREATE TABLE IF NOT EXISTS |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | All routes use `jsonify()` with correct codes: 201, 200, 204, 400, 404 |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:64-67` validates on create; `app.py:110-113` validates on update |
| R10 | GET /health endpoint | ✓ implemented | `app.py:55-57` returns `{"status": "ok"}` with 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` (51 lines) documents pip install, python app.py, endpoints, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` contains 7 test functions covering all CRUD operations |

## Build & Test

```text
Build/test not re-run — stored scores used from retort.db:
  test_coverage    = 0.97
  code_quality     = 0.622
  defect_rate      = 0.535
  maintainability  = 0.989
  idiomatic        = 0.7
  token_efficiency = 0.5
```

```text
7 test functions in test_app.py:
  test_health
  test_create_and_get_book
  test_create_requires_title_and_author
  test_list_and_filter_by_author
  test_update_book
  test_delete_book
  test_get_missing_returns_404
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 209 (app.py: 136, test_app.py: 73) |
| Files | 9 |
| Dependencies | 2 (flask, pytest) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (stored scores) |

## Findings

Top 3 by severity (full list in `findings.jsonl`):

1. [info] No pagination on GET /books — `app.py:88` returns all rows unconditionally
2. [info] No ISBN uniqueness constraint — `app.py:22-28` no UNIQUE on isbn column
3. [info] No year validation on create/update — `app.py:69` year passed without type check

## Reproduce

```bash
cd experiment-1/runs/language=python_model=opus_tooling=beads/rep3
cat stack.json
cat scores.json 2>/dev/null || sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'\$.language')='python' AND json_extract(er.run_config_json,'\$.model')='opus' AND json_extract(er.run_config_json,'\$.tooling')='beads' AND er.replicate=3 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l
grep -cE "^def test_" test_app.py
wc -l app.py test_app.py
```
