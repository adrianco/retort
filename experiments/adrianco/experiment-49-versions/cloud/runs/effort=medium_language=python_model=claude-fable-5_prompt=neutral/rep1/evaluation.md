# Evaluation: effort=medium_language=python_model=claude-fable-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-fable-5, prompt=neutral, effort=medium
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — from scores.json (test_coverage=0.95, defect_rate=1.0)
- **Build:** pass (Python — import succeeds; tests ran)
- **Lint:** pass — code_quality=0.79 (from scores.json)
- **Architecture:** single-module Flask app factory (`create_app`) + SQLite; summary skill unavailable
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:90` create_book — INSERT with title/author/year/isbn, 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:107` list_books — SELECT * FROM books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:111-112` WHERE author = ?; tested `test_app.py:69` |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:117` get_book — 404 at `app.py:121` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:124` update_book — dynamic UPDATE, 404 if absent |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:147` delete_book — 204 / 404 on rowcount 0 |
| R7 | SQLite persistence | ✓ implemented | `app.py:27` sqlite3.connect; schema `app.py:10-18` |
| R8 | JSON + status codes | ✓ implemented | jsonify throughout; 201/200/400/404/204/405 |
| R9 | title & author required | ✓ implemented | `app.py:58-64` validate_payload; tested `test_app.py:44` |
| R10 | GET /health | ✓ implemented | `app.py:86` health → {"status":"ok"} |
| R11 | README with setup/run | ✓ implemented | `README.md` — install, run, endpoints, examples |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` — 7 test functions, all pass |

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
test_coverage = 0.95   (tests executed and passed; 0.95 line coverage)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.68
```

7 test functions in `test_app.py`, 0 skips (`grep pytest.skip|xfail` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 275 (app.py 168, test_app.py 107) |
| Files | 11 (incl. build artifacts) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`) — no high/critical items:

1. [info] PUT supports partial updates beyond the spec (`app.py:133`)
2. [info] Clean error handling for malformed JSON and 404/405 (`app.py:92`, `app.py:156`)

## Reproduce

```bash
cd runs/effort=medium_language=python_model=claude-fable-5_prompt=neutral/rep1
cat scores.json
grep -cE "^def test_" test_app.py
grep -rE "pytest\.skip|xfail" . --include="*.py" | wc -l
```
