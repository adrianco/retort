# Evaluation: rest-api-crud · agent=codex model=gpt-6-luna prompt=neutral · rep 4

## Summary

- **Factors:** language=python, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — defect_rate=1.0 (from scores.json; build+test succeeded)
- **Coverage:** test_coverage=0.78 (from scores.json)
- **Lint / quality:** code_quality=0.79, idiomatic=0.68, maintainability=0.86 (from scores.json)
- **Architecture:** single-module WSGI app (`app.py`), stdlib-only, SQLite persistence; `run-summary` skill not available in this environment
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Pinned checklist from `rest-api-crud-76/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:50-68` INSERT of all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:43-49` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:44-47` `WHERE (? IS NULL OR author = ?)`; test at `test_app.py:33` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:78-82` returns row or 404 |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:83-100` UPDATE + 404 on unknown id |
| R6 | DELETE /books/{id} delete | ✓ implemented | `app.py:101-106` DELETE, 204 / 404 |
| R7 | SQLite persistence | ✓ implemented | `app.py:13-23` `sqlite3.connect`, CREATE TABLE books |
| R8 | JSON responses + status codes | ✓ implemented | `app.py:26-31` JSON encoder; 201/200/404/400/204 used |
| R9 | Validation: title & author required | ✓ implemented | `app.py:58-60`, `app.py:92-93`; test at `test_app.py:37` |
| R10 | GET /health | ✓ implemented | `app.py:41-42` `{"status":"ok"}`; test at `test_app.py:47` |
| R11 | README with setup/run | ✓ implemented | `README.md:1-31` run + API docs |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` has 3 test functions, 0 skips; test_coverage=0.78 > 0 |

## Build & Test

Scores read from `scores.json` (inline gate; run not yet in retort.db). Toolchain not re-run per skill policy.

```text
defect_rate  = 1.0   → build + tests executed and passed
test_coverage= 0.78  → 78% line coverage, tests ran
skips        = 0 (grep pytest.skip/xfail → 0)
test funcs   = 3 (test_app.py)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 115 |
| Lines of code (test_app.py) | 47 |
| Files (source) | 2 (+ README) |
| Dependencies | 0 (stdlib only — no requirements.txt/pyproject) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| code_quality | 0.79 |
| maintainability | 0.86 |
| idiomatic | 0.68 |

## Findings

Full list in `findings.jsonl`. No critical/high/medium findings.

1. [low] Error/edge branches uncovered (coverage 0.78) — `app.py:56-57,66-67` 400/sqlite error paths and `__main__` block untested
2. [info] Bare no-op expression statement — `app.py:110`
3. [info] PUT validates body before checking existence — `app.py:91-98`

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral/rep4"
cat scores.json                       # stored mechanical scores (no re-run)
grep -rE "pytest\.skip|xfail" . --include="*.py" | wc -l   # → 0
grep -cE "^def test_" test_app.py     # → 3
python -m pytest                       # optional: reproduces build+test pass
```
