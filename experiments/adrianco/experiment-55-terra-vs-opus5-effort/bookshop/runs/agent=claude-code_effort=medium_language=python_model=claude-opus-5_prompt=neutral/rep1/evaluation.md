# Evaluation: agent=claude-code effort=medium language=python model=claude-opus-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5, agent=claude-code, effort=medium, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 19 test functions (25 parametrized cases), 0 skipped — all effective; `test_coverage=0.98` (build + tests passed)
- **Build:** pass — imports/collects cleanly (from `test_coverage=0.98`, `defect_rate=1.0` in scores.json)
- **Lint:** pass — `code_quality=0.83` from scores.json
- **Architecture:** app.py (Flask app factory + validation + routes), db.py (SQLite layer), test_app.py (pytest). `run-summary` skill unavailable — see finding I1.
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:127` create_book INSERTs title/author/year/isbn, returns 201 + Location |
| R2 | GET /books lists all | ✓ implemented | `app.py:142` list_books returns full collection ordered by id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:147-150` WHERE author = ? COLLATE NOCASE; tested `test_app.py:111` |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:155` get_book, 404 if absent (`app.py:161`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:164` update_book, 404 on missing (`app.py:173`) |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:178` delete_book returns 204 / 404 |
| R7 | Data stored in SQLite | ✓ implemented | `db.py:7` schema, `db.py:21` sqlite3.connect; persistence test `test_app.py:204` |
| R8 | JSON responses + status codes | ✓ implemented | jsonify throughout; 201/200/204/400/404/405 exercised in tests |
| R9 | Validation: title & author required | ✓ implemented | `app.py:42-49` validate_book; tested `test_app.py:66` |
| R10 | GET /health | ✓ implemented | `app.py:119` health, pings DB, returns 200/503; tested `test_app.py:32` |
| R11 | README with setup/run | ✓ implemented | `README.md` — layout, setup, run, and endpoint docs |
| R12 | ≥ 3 tests | ✓ implemented | 19 test functions in `test_app.py`; `test_coverage=0.98` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
test_coverage = 0.98   # build + tests passed; 98% line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.833
maintainability = 0.852
idiomatic     = 0.87
```

Skip scan (`grep pytest.skip|mark.skip|xfail test_app.py`): 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, app.py+db.py) | ~230 |
| Test LOC (test_app.py) | 209 |
| Files (excl. __pycache__/.coverage) | ~7 source/doc |
| Dependencies (requirements.txt) | 2 (Flask, pytest) |
| Test functions | 19 (25 incl. parametrization) |
| Tests effective | all (0 skipped) |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, no defects:

1. [info] E1 — PUT uses spec-correct full-replace semantics with strict validation
2. [info] E2 — Rejects unknown fields and malformed JSON bodies (robustness beyond spec)
3. [info] I1 — run-summary skill unavailable; architecture summary not generated

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=claude-code_effort=medium_language=python_model=claude-opus-5_prompt=neutral/rep1"
cat scores.json                                  # stored build/test/lint scores
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # skip count
# Optional full re-run: pip install -r requirements.txt && pytest
```
