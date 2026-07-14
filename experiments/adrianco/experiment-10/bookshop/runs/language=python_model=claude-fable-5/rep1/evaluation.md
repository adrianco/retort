# Evaluation: language=python_model=claude-fable-5 · rep 1

## Summary

- **Factors:** language=python, model=claude-fable-5
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — test_coverage=1.0 from scores.json
- **Lint:** warnings — code_quality=0.6222 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 1 items in `findings.jsonl` (0 critical, 0 high, 1 medium)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `app.py:93` `create_book()` accepts all four fields, persists via INSERT |
| R2 | GET /books lists all books | ✓ implemented | `app.py:109` `list_books()` returns full collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:111` checks `request.args.get("author")` and filters query |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `app.py:121` `get_book()` with 404 on missing |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:127` `update_book()` partial update with validation |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:150` `delete_book()` returns 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:4` imports sqlite3; `app.py:10-17` CREATE TABLE schema; `app.py:38` DB init |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | All routes use `jsonify()`; codes: 201 (create), 200 (read/update), 204 (delete), 400 (validation), 404 (not found) |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:51` `validate_payload()` enforces required fields; `test_app.py:44` tests rejection |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:89` returns `{"status": "ok"}`; `test_app.py:27` tests it |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` includes setup, run, API docs, examples, and test instructions |
| R12 | At least 3 unit/integration tests | ✓ implemented | 8 test functions in `test_app.py` covering all endpoints |

## Build & Test

```text
Build+test: test_coverage=1.0 from scores.json (retort scorers already ran pytest)
defect_rate=1.0 — build and all tests passed
```

```text
8 tests total, 0 skipped, 0 failed
Tests cover: health, create, create-validation, non-json-body, list+filter, get-by-id, update, delete
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 173 (app.py) |
| Lines of test code | 111 (test_app.py) |
| Files | 10 |
| Dependencies | 2 (flask, pytest) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| code_quality | 0.6222 |
| idiomatic | 0.88 |
| maintainability | 1.0 |
| token_efficiency | 0.0211 |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [medium] code_quality score 0.62 indicates ruff lint warnings — `.ruff_cache` confirms linter was run

## Reproduce

```bash
cd experiment-10/bookshop/runs/language=python_model=claude-fable-5/rep1
cat scores.json
cat TASK.md
cat stack.json
grep -rE "pytest.skip|@pytest.mark.skip|xfail" . --include="*.py" | wc -l
wc -l app.py test_app.py
```
