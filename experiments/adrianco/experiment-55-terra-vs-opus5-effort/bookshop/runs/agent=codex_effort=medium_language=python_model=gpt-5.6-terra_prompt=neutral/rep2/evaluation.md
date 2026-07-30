# Evaluation: agent=codex_effort=medium_language=python_model=gpt-5.6-terra_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-terra, effort=medium, prompt=neutral, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass (test_coverage=0.93, defect_rate=1.0 from scores.json) — n/a
- **Lint:** pass (code_quality=0.79 from scores.json) — 0 warnings
- **Architecture:** single-module Flask app factory; `run-summary` skill unavailable in this session, so no `summary/index.md` generated
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:36` create_book — INSERT with title/author/year/isbn, 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:52` list_books returns full collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:57-60` WHERE author = ? COLLATE NOCASE; tested `test_app.py:35` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:63` get_book, 404 via `not_found` at `app.py:159` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:70` update_book merges + UPDATE; tested `test_app.py:39` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:89` delete_book, 204 / 404 on rowcount 0 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:100-119` sqlite3 connection + init_db table |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify` everywhere; 201/200/204/400/404/415 codes |
| R9 | title & author required | ✓ implemented | `app.py:148-151` validate_book rejects empty; tested `test_app.py:50` |
| R10 | GET /health | ✓ implemented | `app.py:32` health → `{"status":"ok"}`, 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` setup, run, API, tests sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 3 tests in `test_app.py`; test_coverage=0.93 |

## Build & Test

Not re-run — stored scores read from `scores.json`:

```text
test_coverage = 0.93   (tests ran and passed; ~93% line coverage)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.79
maintainability = 0.88
idiomatic     = 0.73
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 227 (app.py 167, test_app.py 60) |
| Files | 11 (excl. __pycache__/instance/.coverage) |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Non-JSON request bodies return 415 but tests don't exercise that branch — `app.py:132`

No high/critical/medium findings. Clean, spec-complete run.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=medium_language=python_model=gpt-5.6-terra_prompt=neutral/rep2"
cat scores.json
grep -rEn "pytest\.skip|xfail" . --include="*.py" | wc -l
pytest   # optional re-verify
```
