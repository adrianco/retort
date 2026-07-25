# Evaluation: python · hermes-local · gpt-oss-20b-MXFP4-Q8 · neutral · rep 4

## Summary

- **Factors:** language=python, model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8, agent=hermes-local, prompt=neutral, stack=gptoss
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.833` (scores.json); 5 low code-hygiene findings noted below
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 5 low, 0 info)

Mechanical scores read from `scores.json` (no re-run): `test_coverage=0.65`,
`defect_rate=1.0` (build + tests succeeded), `code_quality=0.833`,
`maintainability=0.733`, `idiomatic=0.68`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.py:37 create_book`, persists via `models.py:Book` |
| R2 | GET /books lists all books | ✓ implemented | `main.py:46 list_books` returns `query.all()` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.py:49-50` filters `Book.author == author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.py:54-59`, raises 404 when missing |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.py:62-71`, partial update via `exclude_unset` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.py:74-81`, 404 when missing |
| R7 | Data stored in SQLite | ✓ implemented | `database.py:10 sqlite:///./books.db` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201 create, 200 get/list, 404 missing, 204 delete |
| R9 | Input validation: title & author required | ✓ implemented | `schemas.py:8-9 Field(..., min_length=1)` (rejects with 422, not 400 — see findings) |
| R10 | GET /health | ✓ implemented | `main.py:32-34` returns `{"status": "ok"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` covers install, run, endpoints, tests |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `tests/test_api.py` — 5 tests, `test_coverage=0.65 > 0` |

## Build & Test

Not re-run — mechanical scores taken from `scores.json` (per skill Step 2).

```text
defect_rate = 1.0    → build + tests succeeded
test_coverage = 0.65 → tests executed and passed (coverage fraction, .coverage present)
```

Test inventory (grep): 5 `test_` functions, 0 skips/xfails.
Tests: health, create+get, update, delete+404, author-filter.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (all .py) | 226 |
| Source LOC (main/database/models/schemas) | ~153 |
| Files (excl. caches/.git) | 18 |
| Dependencies (requirements.txt) | 5 (fastapi, uvicorn, sqlalchemy, pydantic, pytest) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [low] R9 — validation rejections return 422, not the 400 the spec implies (`schemas.py:8`)
2. [low] Uses deprecated FastAPI `@app.on_event("startup")` (`main.py:18`)
3. [low] Pydantic v1 idioms (`orm_mode`, `.dict()`) with unpinned deps (`schemas.py:14`, `main.py:39`)
4. [low] DELETE returns a JSON body with a 204 No Content status (`main.py:81`)
5. [low] Validation-rejection path (R9) not covered by a test (`tests/test_api.py`)

No critical/high/medium findings — a clean, fully-conformant run.

## Reproduce

```bash
cd experiments/adrianco/experiment-47-gptoss20b/bookshop/runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--gpt-oss-20b-MXFP4-Q8_prompt=neutral_stack=gptoss/rep4
cat scores.json                       # mechanical scores (build/test/quality)
grep -rE "def test_" tests/           # test inventory
grep -rE "pytest\.skip|xfail" tests/  # skip detection (0)
# build/tests intentionally not re-run — see scores.json
```
