# Evaluation: language=python_model=sonnet_tooling=beads · rep 2

## Summary

- **Factors:** language=python, model=sonnet, tooling=beads
- **Status:** failed (test setup failure due to FastAPI/Starlette version mismatch)
- **Requirements:** 8/10 implemented, 1 partial, 1 missing
- **Tests:** 0 passed / 0 failed / 0 skipped (12 tests defined, all blocked at setup)
- **Build:** pass (Python compilation successful) — <1s
- **Lint:** fail — 12 warnings (imports, type annotations, noqa comment)
- **Architecture:** Book collection API with FastAPI + SQLite
- **Findings:** 15 items in `findings.jsonl` (2 critical, 1 high, 12 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|-------|
| R1 | POST /books create endpoint | ✓ implemented | `main.py:54-63` creates books with validation |
| R2 | GET /books with author filter | ✓ implemented | `main.py:66-75` supports ?author= query param |
| R3 | GET /books/{id} single book | ✓ implemented | `main.py:78-84` retrieves by ID with 404 handling |
| R4 | PUT /books/{id} update endpoint | ✓ implemented | `main.py:87-99` updates fields with validation |
| R5 | DELETE /books/{id} delete endpoint | ✓ implemented | `main.py:102-107` deletes by ID with 404 handling |
| R7 | SQLite database storage | ✓ implemented | `database.py:27-37` creates books table |
| R9 | Input validation (required fields) | ✓ implemented | `main.py:23-28` validates title/author non-empty |
| R10 | Health check endpoint GET /health | ✓ implemented | `main.py:49-51` returns {"status": "ok"} |
| R12 | README.md with instructions | ✓ implemented | `README.md` provides setup, run, endpoints, tests |
| R13 | At least 3 unit/integration tests | ~ partial | 12 tests defined but cannot execute due to setup failure |

## Build & Test

**Python Compilation:**
```text
✓ Compilation passed — all .py files valid Python
```

**Test Execution:**
```text
FAILED: pytest test_books.py -v
Exit code: 1
Error: TypeError: Router.__init__() got an unexpected keyword argument 'on_startup'
  at main.py:14: app = FastAPI(title="Book Collection API", lifespan=lifespan)

Root cause: FastAPI 0.115.0 uses lifespan context manager API, but installed 
Starlette version does not support it. Requires Starlette >= 0.41.0.

12 tests defined but all fail at fixture setup stage.
```

**Lint Check:**
```text
ruff check found 12 issues:
- I001 (import sorting): database.py, main.py, test_books.py (4 locations)
- UP045 (type annotations): use X | None instead of Optional[X] (7 instances)
- F401 (unused import): database imported but not used (test_books.py:29)
- Invalid noqa: test_books.py:29 should specify error codes
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 272 |
| Files | 9 |
| Dependencies | 6 (fastapi, uvicorn, pydantic, pytest, httpx, pytest-asyncio) |
| Tests defined | 12 |
| Tests effective | 0 (execution blocked) |
| Skip ratio | 0% |
| Build duration | <1s |
| Lint warnings | 12 |

## Code Quality Observations

**Strengths:**
- Comprehensive endpoint implementation covering all CRUD operations
- Input validation using Pydantic field validators
- Proper HTTP status codes (201 for creation, 404 for not found, 204 for delete)
- Good test coverage design (12 tests covering happy path and edge cases)
- Clean separation: main.py (routes), database.py (persistence)
- SQLite with proper transaction handling (commit/rollback)
- Author filter uses parameterized query (LIKE ?) to prevent SQL injection

**Critical Issues:**
1. **Dependency Version Mismatch** — FastAPI 0.115.0 requires Starlette >= 0.41.0 but a older version is installed. Prevents all tests from running.
2. **SQL Injection Risk** — update_book() at main.py:95 constructs SQL using f-string with column names, bypassing parameterization. Allows arbitrary SQL injection via field names.

**Medium Issues:**
- Import sorting inconsistencies (fixable with `ruff check --fix`)
- Outdated `Optional[T]` type hints (should use `T | None` for Python 3.10+)

## Findings Summary

By severity (full list in `findings.jsonl`):

1. [critical] Test suite fails at initialization due to FastAPI/Starlette version incompatibility
2. [critical] SQL injection vulnerability in update_book() method uses f-string for column name construction
3. [high] Test execution blocked — all 12 tests cannot run due to setup failure
4. [low] Import sorting violations (ruff I001)
5. [low] Type annotation style warnings (ruff UP045)

## Reproduce

```bash
cd experiment-1/runs/language=python_model=sonnet_tooling=beads/rep2

# Check Python syntax
python -m py_compile main.py database.py test_books.py

# Run linter
ruff check .

# Attempt tests (will fail due to version mismatch)
pytest test_books.py -v

# To fix and run:
# 1. Update Starlette in requirements.txt: starlette>=0.41.0
# 2. Fix SQL injection in main.py:95 (use parameterized column names)
# 3. Run: pip install -r requirements.txt && pytest test_books.py -v
```

## Analysis

This run produced a well-structured REST API with all required endpoints implemented and good design patterns (validation, error handling, transaction safety). However, it is blocked from validation due to:

1. **Blocking Test Failure** — The entire test suite fails at setup. This appears to be a version incompatibility in the generated requirements.txt (FastAPI 0.115.0 expects a newer Starlette than installed).

2. **Security Vulnerability** — The update_book method constructs SQL using f-strings, allowing SQL injection if an attacker can control the update field names. This needs immediate fix before production use.

These issues prevent this run from being fully verified against the task requirements despite having clean, logically correct implementation of the API contract.
