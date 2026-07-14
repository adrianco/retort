# Evaluation: language=python_model=claude-opus-4-7_tooling=none · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-4-7, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 19 passed / 0 failed / 0 skipped (19 effective)
- **Build:** pass — test_coverage=1.0 from retort.db
- **Lint:** code_quality=0.772 from retort.db
- **Architecture:** summary skill not invoked (single-file app, architecture is trivial)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✓ implemented | `app.py:157-162` do_POST → `app.py:205-222` _create_book; test: test_create_book_returns_201_with_body |
| R2 | GET /books lists all books | ✓ implemented | `app.py:144-146` routes to `app.py:186-195` _list_books; test: test_list_books_returns_all |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:188-193` WHERE author = ? on query param; test: test_list_books_filters_by_author |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `app.py:148-154` → `app.py:197-203` _get_book with 404; test: test_get_book_by_id |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:164-170` → `app.py:224-246` _update_book (full + partial); tests: test_update_book_full, test_update_book_partial |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:175-184` → `app.py:248-257` _delete_book returns 204; test: test_delete_book |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:17-28` get_connection uses sqlite3; `app.py:31-43` CREATE TABLE books |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `app.py:108-114` _send_json; uses 200, 201, 204, 400, 404 throughout |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:56-98` validate_book_payload checks required fields; tests: test_create_missing_title_returns_400, test_create_missing_author_returns_400 |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:142-143` returns {"status": "ok"} with 200; test: test_health_endpoint |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 82 lines covering setup, run, endpoints, examples, status codes, tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` — 19 test methods covering all CRUD endpoints, validation, error paths |

## Build & Test

```text
Build + test scores from retort.db (not re-run):
  test_coverage = 1.0  (build + all tests passed)
  code_quality  = 0.772
  defect_rate   = 1.0  (build+test succeeded)
  maintainability = 1.0
  idiomatic     = 0.68
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 499 (278 app.py + 221 test_app.py) |
| Files | 3 (app.py, test_app.py, README.md) |
| Dependencies | 0 (stdlib only) |
| Tests total | 19 |
| Tests effective | 19 |
| Skip ratio | 0% |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [info] Zero external dependencies — stdlib-only implementation
2. [info] Author filter uses exact match, not substring/case-insensitive

## Reproduce

```bash
cd experiment-6/runs/language=python_model=claude-opus-4-7_tooling=none/rep1
cat stack.json
cat TASK.md
# Scores were read from retort.db, not re-run
sqlite3 ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id = (SELECT er.id FROM experiment_runs er WHERE json_extract(er.run_config_json,'$.language')='python' AND json_extract(er.run_config_json,'$.model')='claude-opus-4-7' AND json_extract(er.run_config_json,'$.tooling')='none' AND er.replicate=1 AND er.status='completed' ORDER BY er.finished_at DESC LIMIT 1);"
```
