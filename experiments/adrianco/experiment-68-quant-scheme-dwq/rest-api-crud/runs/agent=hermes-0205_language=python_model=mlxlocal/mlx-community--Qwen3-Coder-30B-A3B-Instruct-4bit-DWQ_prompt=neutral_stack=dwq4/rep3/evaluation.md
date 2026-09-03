# Evaluation: dwq4 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlxlocal/Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ, prompt=neutral, stack=dwq4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — `test_coverage=0.93`, `defect_rate=1.0` from scores.json
- **Build:** pass (Flask app imports; `defect_rate=1.0`)
- **Lint:** n/a — `code_quality=0.7888` from scores.json
- **Architecture:** single-module Flask + sqlite3 (`app.py`); run-summary skill not invoked (unavailable)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:40-74` INSERT + 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:76-93` returns list, 200 |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:83-88` filters on query param |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:95-109` 200 / 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:111-152` UPDATE, 200/404 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:154-173` DELETE, 200/404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:2,12,16-24` sqlite3 books.db table |
| R8 | JSON responses + HTTP status codes | ✓ implemented | jsonify + 201/200/404/400/500 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:46` (POST), `app.py:117` (PUT) → 400 |
| R10 | GET /health | ✓ implemented | `app.py:35-38` returns `{"status":"healthy"}`, 200 |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` setup, run, test, DB sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 8 tests, `test_coverage=0.93` |

## Build & Test

Scores read from `scores.json` (not re-run per evaluate-run skill):

```text
test_coverage = 0.93   # build + tests executed, ~93% coverage/pass
defect_rate   = 1.0    # build + tests succeeded
code_quality  = 0.7888
maintainability = 0.9885
idiomatic     = 0.70
```

Test suite (`test_app.py`), 8 tests, no skips: health, create, list-all, get-by-id, update, delete (+ verify 404), author filter, missing-required-field (400).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 176 |
| Lines of code (test_app.py) | 201 |
| Files (source) | 4 (app.py, test_app.py, requirements.txt, README.md) |
| Dependencies | 1 (Flask==2.3.3) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |

## Findings

All findings are low/info — no requirement gaps, no failures:

1. [low] Tests share a fixed `books.db` in cwd; setUp relies on tearDown cleanup (`test-isolation-1`)
2. [info] 8 tests delivered, exceeding the 3-test minimum (`enh-tests`)
3. [info] PUT enforces title/author and returns 404 for unknown id (`enh-put-validation`)

## Reproduce

```bash
cd "runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ_prompt=neutral_stack=dwq4/rep3"
cat scores.json
pip install -r requirements.txt
python -m pytest test_app.py -v
```
