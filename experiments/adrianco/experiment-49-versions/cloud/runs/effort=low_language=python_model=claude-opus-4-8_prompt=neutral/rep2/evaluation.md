# Evaluation: effort=low_language=python_model=claude-opus-4-8_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-4-8, effort=low, prompt=neutral (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective) — from `scores.json` test_coverage=0.95
- **Build:** pass — from `scores.json` defect_rate=1.0 (not re-run)
- **Lint:** pass — code_quality=0.7889 from `scores.json` (not re-run)
- **Architecture:** run-summary skill unavailable — single-module Flask app (`app.py`) with an app-factory (`create_app`), SQLite persistence, 8-test integration suite (`test_app.py`)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:82` create_book — inserts title/author/year/isbn, returns 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:104` list_books — returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:107-111` filters by `author` query param |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.py:116` get_book — 404 when row is None |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:126` update_book — merges + 404 guard |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:156` delete_book — returns 204, 404 guard |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:5,15-40` sqlite3 connection + CREATE TABLE |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify(...)` with 201/200/404/400/204 throughout |
| R9 | Validation: title+author required | ✓ implemented | `app.py:54-76` validate_payload; test `app.py:45` |
| R10 | GET /health | ✓ implemented | `app.py:78-80` returns `{"status":"ok"}`, 200 |
| R11 | README with setup + run | ✓ implemented | `README.md` — Setup/Run/Endpoints/Examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 8 tests, test_coverage=0.95 |

## Build & Test

Not re-run — stored scores read from `scores.json` (per evaluate-run skill, step 2):

```text
test_coverage = 0.95   # build + tests executed and passed (8 tests, 0 skips)
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.7889 # lint/quality
maintainability = 0.9697
idiomatic     = 0.7
```

Skip scan (`grep pytest.skip|xfail`): 0 skipped tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py + test_app.py) | 268 |
| Files | 12 (incl. archive artifacts) |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [low] Flask runs with `debug=True` bound to `0.0.0.0` — `app.py:173`
2. [info] Test suite exceeds the 3-test minimum (8 tests, edge cases) — enhancement
3. [info] PUT supports partial updates with field-level validation — enhancement

## Reproduce

```bash
cd runs/effort=low_language=python_model=claude-opus-4-8_prompt=neutral/rep2
cat scores.json                                    # stored mechanical scores
grep -rE "pytest\.skip|xfail" . --include="*.py"   # skip scan (0)
grep -cE "^\s*def test_" test_app.py               # test count (8)
```
