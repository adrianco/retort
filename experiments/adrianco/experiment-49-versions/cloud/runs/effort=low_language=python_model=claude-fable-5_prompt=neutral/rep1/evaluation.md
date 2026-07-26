# Evaluation: effort=low_language=python_model=claude-fable-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-fable-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — from `scores.json` (`test_coverage=0.98`, `defect_rate=1.0`)
- **Lint:** pass — `code_quality=0.7888`, `maintainability=1.0`, `idiomatic=0.58` (from `scores.json`)
- **Architecture:** single Flask app factory (`create_app`) over SQLite; see below
- **Findings:** 2 info items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:70-83` create_book, INSERT + 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:85-93` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:88-90` filters on author param |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:95-100` get_book, 404 if absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:102-124` update_book, partial merge |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:126-133` delete_book, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1-39` sqlite3 + schema |
| R8 | JSON + correct status codes | ✓ implemented | `jsonify` + 201/200/400/404/204 throughout |
| R9 | Validation: title/author required | ✓ implemented | `app.py:50-64` validate() → 400 |
| R10 | GET /health | ✓ implemented | `app.py:66-68` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, endpoints, tests |
| R12 | >= 3 unit/integration tests | ✓ implemented | `test_app.py` — 12 tests, `test_coverage=0.98` |

Prompt factor (neutral): P1 — "include tests that demonstrate the implementation meets
the requirements" — satisfied; the 12 tests cover every route and validation path.

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.98   -> build + tests executed and passed
defect_rate   = 1.0    -> build+test succeeded
maintainability = 1.0
code_quality  = 0.7888
idiomatic     = 0.58
```

Test skip scan: `grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail"` → 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 241 (app.py 141, test_app.py 100) |
| Files | 11 (incl. artifacts) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (scores cached) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Neutral prompt satisfied: tests demonstrate requirements
2. [info] Validation covers partial updates and type checks beyond spec

No critical/high/medium/low findings — clean run.

## Architecture

`run-summary` skill not invoked (not available in this session). Structure is a single
Flask application factory `create_app(db_path)` wiring six CRUD routes plus `/health`
over a SQLite `books` table, with a shared `validate()` helper and per-request `g.db`
connection management. Tests use a `tmp_path`-scoped DB fixture and Flask test client.

## Reproduce

```bash
cd runs/effort=low_language=python_model=claude-fable-5_prompt=neutral/rep1
cat scores.json                      # cached build/test/lint scores
grep -cE "^def test_" test_app.py    # 12 tests
grep -rE "pytest\.skip|xfail" .      # 0 skips
```
