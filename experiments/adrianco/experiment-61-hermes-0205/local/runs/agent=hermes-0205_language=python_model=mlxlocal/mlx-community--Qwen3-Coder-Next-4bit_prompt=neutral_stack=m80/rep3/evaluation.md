# Evaluation: mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective)
- **Build:** pass — from `defect_rate=1.0` (retort.db / scores.json)
- **Lint:** pass — `code_quality=0.83`, no skips
- **Architecture:** single-module Flask app (`app.py`), SQLite persistence; summary skill unavailable
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:78 create_book`, INSERT at `app.py:120` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:60 list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:64-70` WHERE author=? |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:138 get_book`, 404 at `app.py:145` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:152 update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:226 delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:4 import sqlite3`, `app.py:32 CREATE TABLE books` |
| R8 | JSON responses + correct status codes | ✓ implemented | `jsonify(...), 201/200/404/400` throughout |
| R9 | Validation: title and author required | ✓ implemented | `app.py:87-90` returns 400 |
| R10 | GET /health | ✓ implemented | `app.py:54 health_check` → `{status: healthy}, 200` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` (Installation, Running the Server, endpoints) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `tests/test_api.py` — 16 tests, `test_coverage=0.92` |

## Build & Test

Scores read from `scores.json` (inline gate) — build/test/lint not re-run per skill guidance.

```text
test_coverage = 0.92   (tests executed and passed; coverage 92%)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.83   (lint/quality)
16 tests defined in tests/test_api.py, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 245 (app.py) + 285 (tests) = 530 |
| Files | app.py, tests/test_api.py, tests/__init__.py, README.md, requirements.txt |
| Dependencies | 1 (flask>=2.0.0) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| test_coverage | 0.92 |
| maintainability | 0.27 |
| idiomatic | 0.65 |

## Findings

Full list in `findings.jsonl` (both info-level, no deductions):

1. [info] Low maintainability index (0.27) — validation logic duplicated across POST/PUT
2. [info] DATABASE module global patched by tests rather than configured via env/app config

## Reproduce

```bash
cd "experiments/adrianco/experiment-61-hermes-0205/local/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep3"
cat scores.json                                          # stored mechanical scores
grep -rE "def test_" tests/ | wc -l                      # 16 tests
grep -rE "skip|xfail" tests/ --include="*.py" | wc -l    # 0 skips
python -m pytest tests/ -q                               # optional re-run
```
