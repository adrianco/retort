# Evaluation: effort=medium_language=python_model=claude-opus-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5, prompt=neutral, effort=medium (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 25 passed / 0 failed / 0 skipped (25 effective) — test_coverage=0.99 from scores.json
- **Build:** pass — from scores.json (defect_rate=1.0 ⇒ build+test succeeded)
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `bookapi/main.py:create_book` INSERTs all four fields, returns 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `bookapi/main.py:list_books` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `main.py:list_books` adds `WHERE author = ?`; tested `test_list_books_filters_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.py:get_book` + `_fetch_book` raises 404; tested `test_get_missing_book_returns_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.py:update_book` full replace, 404-checks first; tested `test_update_book_replaces_all_fields` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.py:delete_book` returns 204; tested `test_delete_book_returns_204_and_removes_it` |
| R7 | Data in SQLite | ✓ implemented | `bookapi/db.py` — `sqlite3` with `books` table, `BOOKS_DB_PATH` override |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/204/404/409/422 across routes; response_model=Book |
| R9 | Validation: title + author required | ✓ implemented | `schemas.py:BookIn` Field(min_length=1) + strip; tested `test_missing_required_fields_rejected` (returns 422, see findings) |
| R10 | GET /health | ✓ implemented | `main.py:health` returns `{"status":"ok"}`, pings DB |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, run, curl examples, layout, design notes |
| R12 | ≥3 unit/integration tests | ✓ implemented | 25 tests across 2 files; test_coverage=0.99 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.99   # build + tests passed (25 tests, 0 skips)
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.8333 # lint/quality
maintainability = 0.924
idiomatic     = 0.5
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 503 |
| Files (excl. build artifacts/logs) | 16 |
| Dependencies (runtime) | 3 (fastapi, uvicorn, pydantic) |
| Tests total | 25 |
| Tests effective | 25 |
| Skip ratio | 0% |
| Build | pass (from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational:

1. [info] R9 — Validation rejects with HTTP 422 (FastAPI default) rather than the 400 named in the spec. Requirement is met (input is rejected with an appropriate 4xx); noted for cross-run status-code comparison.
2. [info] R8 — Duplicate ISBN handled with 409 Conflict (enhancement beyond spec).

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=medium_language=python_model=claude-opus-5_prompt=neutral/rep1
cat scores.json                              # stored build/test/lint scores
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/   # 0 skips
grep -rhE "^def test_" tests/ | wc -l        # 25 tests
# Optional live run:
pip install -r requirements-dev.txt && pytest -q
```
