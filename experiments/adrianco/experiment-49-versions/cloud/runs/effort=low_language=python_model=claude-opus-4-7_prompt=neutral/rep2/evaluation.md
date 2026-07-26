# Evaluation: effort=low_language=python_model=claude-opus-4-7_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-4-7, prompt=neutral, effort=low (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — from `test_coverage=0.94`, `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.79` (scores.json); 1 low lint note (dead code)
- **Architecture:** single-module Flask + SQLite app (`app.py`); `run-summary` skill unavailable in this session — not run
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

Denominator fixed by `REQUIREMENTS.json` (12 items).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:57` create_book, INSERT at :70; test_create_and_get_book |
| R2 | GET /books lists all books | ✓ implemented | `app.py:78` list_books; test_list_and_filter |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:82-83` filters by author param; test asserts len==2 |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:88` get_book, 404 at :93; test_not_found |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:96` update_book, partial-update semantics; test_update_and_delete |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:119` delete_book returns 204; test_update_and_delete |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:11,43` sqlite3.connect; schema at :16-26 |
| R8 | JSON responses + appropriate status codes | ✓ implemented | jsonify throughout; 201/200/204/404/400 (`app.py:76,86,127,93,63`) |
| R9 | Validation: title and author required | ✓ implemented | `app.py:62-65` (create), :107-110 (update); test_create_validation |
| R10 | GET /health endpoint | ✓ implemented | `app.py:53` health returns {"status":"ok"}, 200; test_health |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Setup/Run/Endpoints/Test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 6 tests, all pass (test_coverage=0.94) |

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology and asks for tests demonstrating the requirements — satisfied by R12; no additional P-requirements.

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance). Agent log confirms the test run:

```text
pytest -v
============================== 6 passed in 0.05s ===============================
test_health / test_create_and_get_book / test_create_validation /
test_list_and_filter / test_update_and_delete / test_not_found  — all PASSED
```

Stored scores: test_coverage=0.94, defect_rate=1.0, code_quality=0.79, maintainability=0.99, idiomatic=0.65, token_efficiency=0.011.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 204 (app.py 133 + test_app.py 71) |
| Files | 12 (incl. logs/artifacts); 4 authored source (app.py, test_app.py, README.md, requirements.txt) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores from archive) |

## Findings

Full list in `findings.jsonl`:

1. [low] `get_db()` is dead code — never called (`app.py:8`); routes use `g._database` from the before_request hook.
2. [info] Appropriate HTTP status codes used throughout (201/204/404/400).

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=low_language=python_model=claude-opus-4-7_prompt=neutral/rep2
cat scores.json                              # stored mechanical scores
cat ../../../REQUIREMENTS.json               # pinned 12-item checklist
grep -rEc "^def test_" test_app.py           # 6 tests
grep -rE "pytest\.skip|xfail" test_app.py    # 0 skips
```
