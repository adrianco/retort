# Evaluation: mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80 · rep 2

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.83` (scores.json); 2 unused imports
- **Architecture:** single-module Flask app (`app.py`) + pytest suite (`test_app.py`); `summary/` not generated
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:55` create_book, INSERT at `app.py:95` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:108` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:116` `WHERE author = ?` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:125` get_book, 404 at `app.py:133` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:138` update_book, dynamic UPDATE |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:213` delete_book |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:17` sqlite3.connect, `init_db` at `app.py:30` |
| R8 | JSON responses + correct status codes | ✓ implemented | jsonify + 201/200/404/400 throughout |
| R9 | Validation: title and author required | ✓ implemented | `app.py:64-67` returns 400 |
| R10 | GET /health health check | ✓ implemented | `app.py:49` health_check → 200 |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` Setup/Testing/Usage sections |
| R12 | At least 3 tests | ✓ implemented | 16 tests in `test_app.py`, test_coverage=0.92 |

## Build & Test

Not re-run — stored scores used (per skill Step 2):

```text
scores.json: test_coverage=0.92, defect_rate=1.0, code_quality=0.833,
             token_efficiency=1.0, maintainability=0.270, idiomatic=0.58
_agent_stdout.log: "Test results: 16/16 tests passing"
```

16 tests, 0 skips (`grep pytest.skip|xfail test_app.py` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 242 |
| Lines of code (test_app.py) | 340 |
| Files (excl. caches) | ~7 source/artifact |
| Dependencies | 2 (flask, pytest) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| API calls | 21 |
| Tokens (total) | 642,391 |

## Findings

Full list in `findings.jsonl`. Highest severity is `low`:

1. [low] Unused imports `json`, `re` in app.py
2. [low] Dead test helper `create_test_app` never called
3. [info] PUT with empty `{}` body updates only `updated_at` (not spec-required)

## Reproduce

```bash
cd "experiments/adrianco/experiment-61-hermes-0205/local/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep2"
cat scores.json          # stored mechanical scores (no re-run)
grep -cE "^def test_" test_app.py
grep -rEc "pytest\.skip|xfail" test_app.py
```
