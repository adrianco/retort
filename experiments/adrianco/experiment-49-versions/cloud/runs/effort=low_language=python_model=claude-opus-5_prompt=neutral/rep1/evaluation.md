# Evaluation: effort=low_language=python_model=claude-opus-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — from `test_coverage=1.0` (scores.json)
- **Build:** pass — `test_coverage=1.0` implies build + all tests passed
- **Lint:** pass — `code_quality=0.79` (scores.json); no re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:84 create_book`, INSERT + 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:94 list_books` returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:99-102` WHERE author = ? |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:115 get_book` via `_fetch` (404) |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:120 update_book`, UPDATE |
| R6 | DELETE /books/{id} delete | ✓ implemented | `app.py:133 delete_book`, 204 |
| R7 | SQLite persistence | ✓ implemented | `app.py:17-36` sqlite3 + CREATE TABLE; `test_app.py:76` verifies file |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/204/404/422 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `app.py:44-56` Field(min_length=1) + not_blank; `test_app.py:37` |
| R10 | GET /health | ✓ implemented | `app.py:79 health` → `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, tests, endpoints, examples |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` 8 tests, 0 skips; `test_coverage=1.0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json`:

```text
test_coverage = 1.0   → build + all tests passed
defect_rate   = 1.0   → build+test succeeded
code_quality  = 0.789
maintainability = 1.0 · idiomatic = 0.84
```

8 test functions in `test_app.py`, 0 skipped/xfail (grep confirmed).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 138 (app.py) + 83 (test_app.py) = 221 |
| Files | 10 (incl. artifacts) |
| Dependencies | 4 (requirements.txt) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] R9 — validation returns 422 (FastAPI-standard) rather than the spec-hint's 400; requirement fully enforced, no action needed.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=low_language=python_model=claude-opus-5_prompt=neutral/rep1
cat scores.json                      # mechanical scores (no re-run)
grep -cE "^def test_" test_app.py    # 8
grep -rE "pytest\.skip|xfail" test_app.py | wc -l   # 0
# Optional live run:
pip install -r requirements.txt && pytest -q
```
