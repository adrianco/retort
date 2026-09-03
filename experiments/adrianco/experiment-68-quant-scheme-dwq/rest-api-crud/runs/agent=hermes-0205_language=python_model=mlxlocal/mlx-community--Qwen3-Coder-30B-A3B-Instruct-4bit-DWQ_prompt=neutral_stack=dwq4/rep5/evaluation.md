# Evaluation: dwq4 · rep 5

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ, prompt=neutral, stack=dwq4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — test_coverage=0.94 from scores.json
- **Build:** pass — defect_rate=1.0 from scores.json (Flask app imports/runs; tests execute)
- **Lint:** pass — code_quality=0.79 from scores.json
- **Architecture:** single-module Flask app (`app.py`) + `test_app.py`; run-summary skill unavailable in this session
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:46-80` create_book; test_app.py:50 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:82-98` get_books; test_app.py:87 |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:88-91` LIKE filter; test_app.py:228 |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:100-114`; test_app.py:110,136 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:116-157`; test_app.py:143,180 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:159-182`; test_app.py:195,221 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:16-39` sqlite3, books table, books.db |
| R8 | JSON responses + correct status codes | ✓ implemented | `app.py` jsonify with 201/200/404/400/500 |
| R9 | Validation: title & author required | ✓ implemented | `app.py:52,122` returns 400; test_app.py:72 |
| R10 | GET /health health check | ✓ implemented | `app.py:41-44`; test_app.py:43 |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` setup/run/test sections |
| R12 | >= 3 unit/integration tests | ✓ implemented | 11 tests in `test_app.py`; test_coverage=0.94 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.94   → build + tests executed and passed
defect_rate   = 1.0    → build+test succeeded
code_quality  = 0.79
maintainability = 0.98
idiomatic     = 0.42
```

11 tests defined, 0 skipped (grep of test_app.py for skip/xfail markers = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 186 |
| Lines of code (test_app.py) | 274 |
| Files (source) | 3 (app.py, test_app.py, README.md) |
| Dependencies | 1 (Flask==2.3.3) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |

## Findings

Full list in `findings.jsonl`:

1. [low] README states port 5000 but app serves on 5001 (README.md:34 vs app.py:187)
2. [info] Author filter uses LIKE substring match rather than exact match (app.py:91)

No critical/high/medium findings. All 12 pinned requirements implemented and exercised by tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-68-quant-scheme-dwq/rest-api-crud/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit-DWQ_prompt=neutral_stack=dwq4/rep5"
cat scores.json                                    # stored build/test/lint scores
grep -cE "def test_" test_app.py                   # 11 tests
grep -rE "skip|xfail" test_app.py | wc -l          # 0 skips
python -m pytest test_app.py                       # (fallback only) re-run tests
```
