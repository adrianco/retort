# Evaluation: agent=hermes-local · language=python · model=Qwen3-Coder-Next-4bit (80B) · stack=m80 · prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, stack=m80, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective)
- **Build:** pass (from scores.json — `defect_rate=1.0`, `test_coverage=0.98`)
- **Lint:** pass — `code_quality=0.83` from scores.json (no run-time lint executed; not re-run per skill)
- **Architecture:** run-summary skill unavailable in this session — see inline structure below
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 2 low, 1 info)

Scores read from `scores.json` (inline gate output; DB not re-queried):
`code_quality=0.833, token_efficiency=1.0, test_coverage=0.98, defect_rate=1.0, maintainability=0.300, idiomatic=0.9`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.py:38 create_book`; persists via `database.py:Book` |
| R2 | GET /books lists all books | ✓ implemented | `main.py:53 list_books` → `db.query(Book).all()` |
| R3 | GET /books ?author= filter | ✓ implemented | `main.py:59-60 filter(Book.author == author)`; test_api.py:119 |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.py:66-72`; raises 404; test_api.py:138,144 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.py:75-88`; partial update via exclude_unset; test_api.py:164 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.py:91-100`; 204; test_api.py:185 |
| R7 | Data stored in SQLite | ✓ implemented | `database.py:7 sqlite:///./books.db`; SQLAlchemy models |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201 create, 200 get/list, 404 not-found, 204 delete, 422 validation |
| R9 | Validation: title & author required | ✓ implemented | `schemas.py:9-10 Field(..., min_length=1)`; test_api.py:75,85 (422) |
| R10 | GET /health health-check | ✓ implemented | `main.py:24 health_check` returns healthy; test_api.py:49. See F1 — DB probe masked. |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — install, run, curl examples, test cmd |
| R12 | ≥3 unit/integration tests | ✓ implemented | 14 tests in `test_api.py`; test_coverage=0.98 |

## Build & Test

Not re-run per skill (scores already computed). From `scores.json`:

```text
defect_rate    = 1.0    # build + tests succeeded
test_coverage  = 0.98   # coverage / pass signal
code_quality   = 0.833
```

Test inventory (grep `^def test_` in test_api.py): 14 tests, 0 skips/xfail. All endpoints
exercised including 404 paths, author filter, validation rejection, and a multi-op sequence.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, 4 files) | 422 |
| Files (excl. venv/pycache) | 15 |
| Dependencies (requirements.txt) | 6 |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| maintainability (scores.json) | 0.300 |
| token_efficiency (scores.json) | 1.0 |

## Findings

Top items (full list in `findings.jsonl`):

1. [medium] F1 — `/health` DB probe silently fails under SQLAlchemy 2.0 (`db.execute("SELECT 1")` needs `text()`); except branch always taken so health never verifies connectivity (`main.py:30`).
2. [low] F2 — Deprecated `@app.on_event("startup")` hook (`main.py:18`).
3. [low] F3 — Pydantic v2 deprecated `.dict()` call (`main.py:82`).
4. [info] F4 — Validation returns 422 (FastAPI default) vs 400 phrased in TASK.md; satisfies R9.

No critical or high findings — clean implementation of all 12 requirements with passing tests.

## Reproduce

```bash
cd experiments/adrianco/experiment-38-alllang-80b-fullctx/bookshop/runs/agent=hermes-local_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep2
cat scores.json                                   # stored build/test/quality scores
grep -cE "^def test_" test_api.py                 # 14 tests
grep -rEn "pytest\.skip|xfail" . --include="*.py" | grep -v venv | wc -l   # 0 skips
wc -l main.py database.py schemas.py test_api.py  # 422 LOC
```
