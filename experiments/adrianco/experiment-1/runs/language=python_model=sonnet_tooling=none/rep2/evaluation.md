# Evaluation: language=python_model=sonnet_tooling=none · rep 2

## Summary

- **Factors:** language=python, model=sonnet, tooling=none
- **Status:** failed (test_coverage=0.0 — tests did not execute)
- **Requirements:** 11/12 implemented, 1 partial, 0 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective) — test gate failure, test_coverage=0.0 from retort.db
- **Build:** fail — test_coverage=0.0 from retort.db (run_id=17)
- **Lint:** unavailable — code_quality=0.0 from retort.db
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (1 critical, 1 high)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book | ✓ implemented | `main.py:72-82` — `create_book` accepts title, author, year, isbn via `BookCreate` model, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `main.py:85-94` — `list_books` returns all rows |
| R3 | GET /books ?author= filter | ✓ implemented | `main.py:86-91` — `author` query param with LIKE filter |
| R4 | GET /books/{id} single book | ✓ implemented | `main.py:97-103` — `get_book` with 404 on missing |
| R5 | PUT /books/{id} updates | ✓ implemented | `main.py:106-121` — `update_book` partial update, 404 on missing |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `main.py:124-131` — `delete_book` with 204, 404 on missing |
| R7 | SQLite storage | ✓ implemented | `main.py:1,7,12-29` — `sqlite3` module, `books.db`, CREATE TABLE |
| R8 | JSON + correct HTTP status codes | ✓ implemented | 201 create, 200 get/list/update, 204 delete, 404 not found, 400 no fields |
| R9 | Input validation (title, author required) | ✓ implemented | `main.py:35-47` — pydantic `BookCreate` with `field_validator` rejecting empty strings |
| R10 | GET /health endpoint | ✓ implemented | `main.py:67-69` — returns `{"status": "ok"}` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — pip install, uvicorn command, endpoint table, curl examples |
| R12 | At least 3 unit/integration tests | ~ partial | `test_api.py` has 12 test functions but test_coverage=0.0 — tests did not execute |

## Build & Test

```text
Build/test not re-run — using stored scores from retort.db (run_id=17).
test_coverage=0.0 (tests did not execute)
code_quality=0.0
defect_rate=0.0
All mechanical scores returned 0.0, indicating the scoring environment
failed to run the test suite (likely missing dependencies).
```

```text
Test functions in test_api.py (12 total, 0 skipped):
  test_health_check
  test_create_book
  test_create_book_missing_required_fields
  test_create_book_empty_title
  test_list_books
  test_list_books_filter_by_author
  test_get_book
  test_get_book_not_found
  test_update_book
  test_update_book_not_found
  test_delete_book
  test_delete_book_not_found
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 239 (main.py: 130, test_api.py: 109) |
| Files | 10 |
| Dependencies | 4 (fastapi, uvicorn, pytest, httpx) |
| Tests total | 12 |
| Tests effective | 0 (test_coverage=0.0) |
| Skip ratio | 0% |
| Build duration | 79.8s (_duration_seconds from retort.db) |

## Findings

Top 2 by severity (full list in `findings.jsonl`):

1. [critical] Test gate failure: test_coverage=0.0 — tests did not execute
2. [high] 12 tests exist but did not execute (test_coverage=0.0)

## Reproduce

```bash
cd experiment-1/runs/language=python_model=sonnet_tooling=none/rep2
cat stack.json
cat scores.json 2>/dev/null || echo "scores.json absent"
sqlite3 -readonly ../../retort.db "SELECT rr.metric_name, rr.value FROM run_results rr WHERE rr.run_id=17;"
grep -rE "pytest.skip|@pytest.mark.skip|xfail" . --include="*.py" | wc -l
wc -l main.py test_api.py README.md requirements.txt
grep -cE "^def test_" test_api.py
```
