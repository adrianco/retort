# Evaluation: agent=codex effort=default language=python model=gpt-6-luna prompt=neutral · rep 4

## Summary

- **Factors:** language=python, model=gpt-6-luna, agent=codex, framework=flask, prompt=neutral, effort=default
- **Status:** ok (REPAIR run — a prior attempt failed; this fix passes)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — test_coverage=0.93 from scores.json (build + tests ran and passed)
- **Lint:** pass — code_quality=0.7889 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:73 create_book` INSERTs all four fields |
| R2 | GET /books lists all books | ✓ implemented | `app.py:86 list_books` returns full collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:88-93` WHERE author = ? when param present |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:96 get_book` returns 404 on None |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:104 update_book`, tested in `test_filter_update_delete` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:120 delete_book`, 204/404, tested |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:17-40` sqlite3, `books` table, persistence test `test_app.py:33` |
| R8 | JSON responses + HTTP status codes | ✓ implemented | `jsonify` throughout; 201/200/404/400/204 |
| R9 | Validation: title and author required | ✓ implemented | `app.py:53-59`, tested in `test_validation_and_missing_book` |
| R10 | GET /health | ✓ implemented | `app.py:69 health` returns `{status:"ok"}` 200 |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — setup, run, endpoints, tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 test methods in `tests/test_app.py`; test_coverage=0.93 |

## Build & Test

Scores read from `scores.json` (computed inline during `retort run`); build/tests were **not** re-run.

```text
scores.json
test_coverage = 0.93   (build + all tests ran and passed)
defect_rate   = 1.0    (build+test succeeded)
code_quality  = 0.7889
maintainability = 0.9217
idiomatic     = 0.72
```

```text
tests/test_app.py — 4 test methods, 0 skips
  test_health_and_create_get
  test_validation_and_missing_book
  test_create_accepts_all_fields_and_persists_in_sqlite
  test_filter_update_delete
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 190 (app.py 134 + test_app.py 56) |
| Files | 13 (incl. archive/build noise) |
| Dependencies | 1 (Flask) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational, no deductions:

1. [info] Validation goes beyond spec (unknown-field rejection, type checks) — `app.py:45-67`
2. [info] PUT /books/{id} is a full replace requiring title+author — `app.py:104-118`
3. [info] Module-level `create_app()` runs table creation against real books.db at import — `app.py:131`

## Reproduce

```bash
cd experiments/adrianco/experiment-76-luna6/rest-api-crud/runs/agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral/rep4
cat scores.json                                   # stored mechanical scores
python -m unittest discover -s tests -v           # 4 tests, all pass
grep -rE "skip|xfail" tests/ --include="*.py"     # 0 skips
```
