# Evaluation: language=python_model=sonnet_tooling=beads · rep 3

## Summary

- **Factors:** language=python, model=sonnet, tooling=beads
- **Status:** failed (tests did not execute — dependency import error in scoring environment)
- **Requirements:** 12/12 implemented in code, 0 partial, 0 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (0 effective) — collection error, not test logic failure
- **Build:** fail — prior scorer used `python -m py_compile **/*.py` which failed on glob expansion
- **Lint:** unavailable (retort.db locked, scores.json absent)
- **Architecture:** summary skill not invoked
- **Findings:** 2 items in `findings.jsonl` (1 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `main.py:19-25` — `create_book` accepts all four fields via `schemas.BookCreate` |
| R2 | GET /books lists all books | ✓ implemented | `main.py:28-33` — `list_books` returns `query.all()` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `main.py:29-32` — `Optional[str] = Query(None)` param filters by `Book.author`; tested `test_books.py:69` |
| R4 | GET /books/{id} returns a single book | ✓ implemented | `main.py:36-40` — `get_book` with 404 on missing; tested `test_books.py:79` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.py:43-52` — `update_book` with partial update via `exclude_unset=True`; tested `test_books.py:92` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.py:55-62` — `delete_book` returns 204; tested `test_books.py:106` |
| R7 | Data stored in SQLite | ✓ implemented | `database.py:4` — `sqlite:///./books.db` via SQLAlchemy engine |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | 201 create, 200 get/list/update, 204 delete, 404 not found, 422 validation error |
| R9 | Input validation: title and author required | ✓ implemented | `schemas.py:6-7` — `title: str`, `author: str` (no Optional/default); tested `test_books.py:51,56` |
| R10 | GET /health endpoint | ✓ implemented | `main.py:14-16` — returns `{"status": "ok"}`; tested `test_books.py:36` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — pip install, uvicorn command, endpoint table, curl examples, pytest command |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_books.py` — 12 test functions covering CRUD, validation, 404 handling |

## Build & Test

```text
Prior scorer build command: python -m py_compile **/*.py
Exit code: 1
Cause: shell glob **/*.py not expanded — "No such file or directory"
Note: code has no syntax errors; build failure is a scorer invocation issue
```

```text
Prior scorer test command: pytest -q
Exit code: 2 (collection error)
Cause: ImportError collecting test_books.py — fastapi/sqlalchemy not installed in scorer environment
Result: 0 passed, 0 failed, 0 skipped (0 effective)
Note: 12 well-structured integration tests exist but could not be collected
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 236 |
| Files | 14 |
| Dependencies | 4 (fastapi, uvicorn, sqlalchemy, pytest+httpx) |
| Tests total | 12 |
| Tests effective | 0 (collection error) |
| Skip ratio | 0% |
| Build duration | N/A |

## Findings

Top 2 by severity (full list in `findings.jsonl`):

1. [critical] Tests did not execute — import collection error in scoring environment
2. [info] Validation returns 422 instead of 400 — correct per FastAPI conventions

## Reproduce

```bash
cd experiment-1/runs/language=python_model=sonnet_tooling=beads/rep3
cat stack.json
cat TASK.md
grep -rE "pytest.skip|@pytest.mark.skip|xfail" . --include="*.py" | wc -l
wc -l database.py main.py models.py schemas.py test_books.py
```
