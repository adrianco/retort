# Evaluation: effort=default_language=python_model=claude-fable-5-1_prompt=none · rep 3

## Summary

- **Factors:** language=python, model=claude-fable-5-1, effort=default, prompt=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective)
- **Build:** pass — test_coverage=0.94, defect_rate=1.0 (from `scores.json`)
- **Lint:** pass — code_quality=0.833 (from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:121` create_book → INSERT, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:139` list_books → `SELECT * ORDER BY id` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:143` filters `WHERE author = ? COLLATE NOCASE`; test `:49` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:152` get_book, 404 branch `:156`; test `:75` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:159` update_book full replace; test `:81` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:202` delete_book → 204, 404 branch; test `:118` |
| R7 | Data stored in SQLite | ✓ implemented | `db.py:8` schema, `db.py:20` sqlite3 connection; persistence test `:133` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/404/400/204/405/415 codes |
| R9 | Validation: title and author required | ✓ implemented | `app.py:57` required-field check; test `:19` |
| R10 | GET /health health check | ✓ implemented | `app.py:113` health → `SELECT 1`, status ok; test `:4` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` endpoints, setup, run instructions |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 14 tests in `tests/test_books.py`, test_coverage=0.94 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.94   → build + tests pass (14 passed, 0 failed, 0 skipped)
defect_rate   = 1.0    → build+test succeeded
code_quality  = 0.8333
maintainability = 0.8185
idiomatic     = 0.77
```

## Metrics

| Metric | Value |
|--------|-------|
| Source files (app.py, db.py, tests) | 4 |
| Total files (excl. __pycache__/.git/.coverage) | 16 |
| Dependencies | Flask (runtime); pytest, pytest-cov (dev) |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| test_coverage | 0.94 |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level enhancements, no gaps:

1. [info] PATCH /books/{id} partial-update endpoint beyond spec
2. [info] JSON 405/415 error handlers and ISBN checksum validation beyond spec
3. [info] Cross-instance persistence test confirms real SQLite durability

## Reproduce

```bash
cd "experiments/adrianco/experiment-65-fable51-effort/rest-api-crud/runs/effort=default_language=python_model=claude-fable-5-1_prompt=none/rep3"
cat scores.json                          # mechanical scores (build/test/lint)
grep -rEc "def test_" tests/*.py         # 14 tests
grep -rEc "pytest\.skip|xfail" tests/    # 0 skips
python -m pytest -q                      # optional re-run
```
