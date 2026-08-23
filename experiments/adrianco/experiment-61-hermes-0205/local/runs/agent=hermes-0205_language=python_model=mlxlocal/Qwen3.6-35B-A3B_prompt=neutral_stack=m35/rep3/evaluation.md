# Evaluation: Qwen3.6-35B-A3B_prompt=neutral_stack=m35 · rep 3

## Summary

- **Factors:** language=python, model=mlxlocal/Qwen3.6-35B-A3B, agent=hermes-0205, prompt=neutral, stack=m35
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, denominator=12)
- **Tests:** 15 passed / 0 failed / 0 skipped (15 effective) — from `test_coverage=0.96`
- **Build:** pass — from `test_coverage=0.96` (scores.json; tests executed and passed)
- **Lint:** pass — `code_quality=0.83` (scores.json)
- **Architecture:** single-module Flask app (`app.py`) + SQLite; `run-summary` skill not available in this session (skipped)
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:72-107` create_book, INSERT with 4 fields |
| R2 | GET /books lists all books | ✓ implemented | `app.py:110-124` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:116-120` LIKE match on author |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:127-134`, 404 at :133 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:137-175`, partial-update aware |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:178-188` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:15-27` sqlite3, books table |
| R8 | JSON responses + appropriate status codes | ✓ implemented | jsonify + 201/200/404/400 throughout |
| R9 | Validation: title and author required | ✓ implemented | `app.py:82-85`, 400 on missing |
| R10 | GET /health endpoint | ✓ implemented | `app.py:66-69` returns {"status":"healthy"},200 |
| R11 | README with setup and run instructions | ✓ implemented | `README.md:16-36` setup + run + tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 15 tests, test_coverage=0.96 |

## Build & Test

```text
# Not re-run — stored scores read from scores.json
test_coverage = 0.96  (build + tests executed and passed; 15 tests, 0 skipped)
code_quality  = 0.83
defect_rate   = 1.0   (build+test succeeded)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 433 (app.py 192 + test_app.py 241) |
| Files | app.py, test_app.py, README.md, requirements.txt |
| Dependencies | 2 (flask, pytest) |
| Tests total | 15 |
| Tests effective | 15 |
| Skip ratio | 0% |
| test_coverage | 0.96 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] `?author=` filter is a substring (LIKE %..%) match — acceptable per spec, no action needed.

No correctness, build, test, or requirement findings. Clean run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-61-hermes-0205/local/runs/agent=hermes-0205_language=python_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35/rep3"
cat scores.json                     # stored mechanical scores (no re-run)
grep -c "def test_" test_app.py     # 15
python -m pytest test_app.py -v     # optional local re-run
```
