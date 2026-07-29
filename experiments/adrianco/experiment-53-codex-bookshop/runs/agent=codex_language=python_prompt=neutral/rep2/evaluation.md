# Evaluation: agent=codex language=python prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-luna, prompt=neutral, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass (test_coverage=0.91 from scores.json ⇒ build+tests ran)
- **Lint:** pass — code_quality=0.79 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:30 create_book` — INSERT, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:48 list_books` — SELECT ... ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:51-56` — WHERE author = ? COLLATE NOCASE |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:59 get_book` — 404 via `_not_found` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:66 update_book` — UPDATE, 404 if absent |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:84 delete_book` — DELETE, returns 204 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:3,102 sqlite3.connect`; schema `app.py:115 init_db` |
| R8 | JSON + HTTP status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404 |
| R9 | Validate title & author required | ✓ implemented | `app.py:144 _validate_book` — 400 on missing/empty |
| R10 | GET /health | ✓ implemented | `app.py:26 health` — `{"status": "ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup/Run/Test sections |
| R12 | ≥3 tests | ✓ implemented | `tests/test_api.py` — 4 test functions, 0 skips |

## Build & Test

Scores read from `scores.json` (inline gate; not re-run):

```text
test_coverage = 0.91   ⇒ build + tests executed and passed
defect_rate   = 1.0    ⇒ build+test succeeded
code_quality  = 0.79
maintainability = 0.83
idiomatic     = 0.73
```

Test suite (`tests/test_api.py`): health+create, list-filter+missing, update+delete,
required-field validation. Uses per-test tmp SQLite DB via fixture. 0 skipped/xfail.

Note: `_agent_stderr.log` shows the harness rejected an `rm -rf` cleanup command the agent
attempted; this had no effect on the delivered code (the agent completed successfully).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 215 (app.py 169 + tests 46) |
| Files | 5 source (app.py, tests/test_api.py, README.md, requirements.txt, pyproject.toml) |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (scores from inline gate) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] PUT /books/{id} is full-replace, requires title+author (acceptable — spec only asks for "update")
2. [info] Module-level `create_app()` opens/creates the DB at import time

No critical, high, medium, or low findings. This is a clean, spec-complete implementation.

## Reproduce

```bash
cd "/Users/adriancockcroft/code/retort/experiments/adrianco/experiment-53-codex-bookshop/runs/agent=codex_language=python_prompt=neutral/rep2"
cat scores.json                     # stored build/test/lint scores (not re-run)
grep -cE "^def test_" tests/test_api.py
grep -rE "pytest\.skip|xfail" tests/ --include="*.py" | wc -l
# optional: pip install -r requirements.txt && pytest -q
```
