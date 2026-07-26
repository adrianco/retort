# Evaluation: effort=default·language=python·model=claude-opus-4-7·prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-4-7, prompt=neutral, effort=default (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — via test gate (test_coverage=0.97 from scores.json; not re-run)
- **Lint:** pass — code_quality=0.79 from scores.json (no per-line evidence available)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

All requirements from the pinned `REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:106` create_book, INSERT → 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:127` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:130-135`; `test_app.py:69` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:140` get_book, 404 at `:145` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:148` update_book |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:169` delete_book, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:34` _init_db, sqlite3 throughout |
| R8 | JSON + appropriate status codes | ✓ implemented | jsonify + 200/201/204/400/404 |
| R9 | Validation: title & author required | ✓ implemented | `app.py:50` _validate_payload; `test_app.py:47` |
| R10 | GET /health | ✓ implemented | `app.py:102` health → `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, curl, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | 8 tests in `test_app.py`, test_coverage=0.97 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill guidance):

```text
test_coverage = 0.97   # build + tests executed and passed
defect_rate   = 1.0    # build+test succeeded
maintainability = 1.0
code_quality  = 0.79
idiomatic     = 0.87
```

Skip scan: `grep -Ec "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py` → 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 302 (app.py 182 + test_app.py 120) |
| Files | 11 (incl. logs/artifacts) |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items by severity (full list in `findings.jsonl`) — no critical/high/medium:

1. [low] Dev server binds 0.0.0.0 with no production guidance — `app.py:182`
2. [info] Validation exceeds spec (unknown-field rejection, partial PUT, type checks)
3. [info] 8 tests provided vs 3 required, covering CRUD + 404/400 cases

## Reproduce

```bash
cd runs/effort=default_language=python_model=claude-opus-4-7_prompt=neutral/rep2
cat scores.json
grep -Ec "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py
grep -cE "^def test_" test_app.py
# optional, verify locally:
pip install -r requirements.txt && pytest -v
```
