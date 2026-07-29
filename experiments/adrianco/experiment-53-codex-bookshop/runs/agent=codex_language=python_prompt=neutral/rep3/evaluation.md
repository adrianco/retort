# Evaluation: agent=codex_language=python_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-luna, prompt=neutral, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (defect_rate=1.0 from scores.json — import/build + tests succeeded)
- **Lint:** pass — code_quality=0.7889 from scores.json
- **Architecture:** single-module Flask app-factory (`create_app`) over SQLite; `summary/` skill unavailable this session
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Mechanical scores (scores.json): test_coverage=0.92, defect_rate=1.0, code_quality=0.7889, maintainability=0.8294, idiomatic=0.80, token_efficiency=0.0173.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:79 create_book` INSERT + 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:96 list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:104` LIKE filter; test `test_validation_and_author_filter` |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:110 get_book` with 404 |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:117 update_book` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:137 delete_book` 204/404 |
| R7 | SQLite storage | ✓ implemented | `app.py:13 SCHEMA`, `sqlite3.connect` |
| R8 | JSON + status codes | ✓ implemented | 201/200/404/400/204 across routes |
| R9 | Validate title+author required | ✓ implemented | `app.py:57 validate_book`; test asserts 400 |
| R10 | GET /health | ✓ implemented | `app.py:75 health` → `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` setup + endpoints + tests |
| R12 | ≥3 tests | ✓ implemented | 3 test functions; test_coverage=0.92 (>0) |

## Build & Test

Not re-run — stored scores used per skill (defect_rate=1.0 ⇒ build+tests passed).

```text
scores.json: test_coverage=0.92, defect_rate=1.0
tests/test_app.py: 3 functions, 0 skips (grep pytest.skip/xfail = 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 193 (app.py 151, test 42) |
| Files | 12 |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level, no defects:

1. [info] Author filter is substring LIKE match, not exact (enhancement)
2. [info] Extra validation beyond spec — unknown-field + year/isbn type checks
3. [info] 3 tests bundle multiple assertions each (still meets ≥3)

## Reproduce

```bash
cd "experiments/adrianco/experiment-53-codex-bookshop/runs/agent=codex_language=python_prompt=neutral/rep3"
cat scores.json
grep -cE "^def test_" tests/test_app.py
pytest -q   # optional live re-run
```
