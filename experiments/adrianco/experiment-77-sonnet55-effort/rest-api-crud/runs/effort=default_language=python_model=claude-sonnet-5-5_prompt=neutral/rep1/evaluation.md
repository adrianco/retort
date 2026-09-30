# Evaluation: effort=default·language=python·model=claude-sonnet-5-5·prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — import/collection succeeded (test_coverage=0.93 from scores.json)
- **Lint:** pass — code_quality=0.79 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (fixed denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:125-132` POST → `store.create`; `tests/test_api.py:42` |
| R2 | GET /books lists all | ✓ implemented | `app.py:122-124` → `store.list`; `tests/test_api.py:54` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:123` parses `author`; `store.list` filters (`app.py:43-45`); `tests/test_api.py:58` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:136-137,152-154`; `tests/test_api.py:45,73` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:138-145` → `store.update`; `tests/test_api.py:62` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:146-149` → 204; `tests/test_api.py:70` |
| R7 | Data stored in SQLite | ✓ implemented | `BookStore` uses `sqlite3` (`app.py:5,15-27`) |
| R8 | JSON responses + status codes | ✓ implemented | `_send` (`app.py:98-105`); 201/200/404/400/204/405 used throughout |
| R9 | Validation: title & author required | ✓ implemented | `validate` (`app.py:67-87`); `tests/test_api.py:48` |
| R10 | GET /health | ✓ implemented | `app.py:119-120`; `tests/test_api.py:38` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, endpoints, tests) |
| R12 | ≥3 tests | ✓ implemented | 6 test functions in `tests/test_api.py`; test_coverage=0.93 |

No prompt-factor requirements: `prompt=neutral` is the benchmark's neutral instruction, not an extra checkable spec file.

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output), per skill Step 2:

```text
scores.json: test_coverage=0.93, defect_rate=1.0, code_quality=0.7889,
             maintainability=0.9132, idiomatic=0.72, token_efficiency=0.0273
```

`test_coverage=0.93` (> 0) ⇒ build + tests executed and passed; `defect_rate=1.0` ⇒ build+test succeeded. 6 test functions, 0 skips (`grep` for `pytest.skip`/`xfail` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, app.py) | 171 |
| Test LOC | 74 |
| Files (source + tests + README) | 5 |
| Dependencies (runtime) | 0 (stdlib only) |
| Dependencies (test) | pytest |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Coverage (scores.json) | 0.93 |

## Findings

Full list in `findings.jsonl` (nothing above `low`):

1. [low] All requests serialized through one global lock on a single shared SQLite connection (`app.py:16-18`)
2. [info] Zero-dependency stdlib implementation (`app.py:1-7`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=default_language=python_model=claude-sonnet-5-5_prompt=neutral/rep1"
cat scores.json                                                  # mechanical scores (not re-run)
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ | wc -l  # skip count = 0
grep -rcE "^def test_" tests/test_api.py                         # 6 tests
# To actually re-run (skill says not to): python -m pytest
```
