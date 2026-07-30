# Evaluation: agent=codex_effort=low_language=python_model=gpt-5.6-terra_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=gpt-5.6-terra, agent=codex, effort=low, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.789` (scores.json)
- **Architecture:** single-module Flask app factory (`create_app`) + SQLite; `run-summary` skill unavailable this session
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Denominator fixed by the experiment's pinned `bookshop/REQUIREMENTS.json` (12 items).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:34-45` INSERT of title/author/year/isbn, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:47-57` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:53-56` WHERE author=?; `tests/test_app.py:29` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:59-64`; 404 via `not_found` at `app.py:63` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:66-79` UPDATE; `tests/test_app.py:38` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:81-88` returns 204/404; `tests/test_app.py:45` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:95-114` sqlite3 connect + CREATE TABLE |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404 |
| R9 | title & author required | ✓ implemented | `app.py:122-127`; `tests/test_app.py:50` |
| R10 | GET /health | ✓ implemented | `app.py:30-32` returns `{"status":"ok"}`; `tests/test_app.py:57` |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, endpoints, tests sections |
| R12 | >= 3 tests | ✓ implemented | 5 test functions in `tests/test_app.py`; `test_coverage=0.94` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.94   # tests executed and passed (coverage fraction)
defect_rate   = 1.0    # build + tests succeeded
code_quality  = 0.789
maintainability = 0.896   idiomatic = 0.8
```

```text
pytest -q  (5 tests: create/get, author filter, update/delete, validation, health)
0 skips / 0 xfail  →  5 effective tests
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 216 (app.py 156, tests 60) |
| Files | 14 |
| Dependencies | 1 (Flask) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] PUT /books/{id} is a full replace, clearing omitted optional fields — intended semantics, documented in README.
2. [info] Input validation extends beyond spec minimum (year/isbn type checks).

No critical/high/medium/low findings: all 12 requirements implemented, tests pass, no skips.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=low_language=python_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json                                  # stored build/test/lint scores
grep -rE "pytest\.skip|xfail" tests/             # 0 skips
grep -cE "def test_" tests/test_app.py           # 5 tests
pytest -q                                        # optional re-run (build+tests)
```
