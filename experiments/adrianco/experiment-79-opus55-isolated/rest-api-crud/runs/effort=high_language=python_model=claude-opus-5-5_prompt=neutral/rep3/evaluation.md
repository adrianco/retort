# Evaluation: rest-api-crud · effort=high language=python model=claude-opus-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=high
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 70 passed / 0 failed / 0 skipped (70 effective)
- **Build:** pass — from `scores.json` (`test_coverage=0.97`, `defect_rate=1.0`; std-lib only, no build step)
- **Lint:** pass — `code_quality=0.833` from `scores.json`
- **Architecture:** `run-summary` skill unavailable in this session; module map below
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

Denominator is the pinned 12-item `REQUIREMENTS.json` (constant across all runs of this task).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `books_api/app.py:138` `_create_book`; `db.py:51` `create`; `test_api.py:29` |
| R2 | GET /books lists all | ✓ implemented | `app.py:133` `_list_books`; `db.py:60`; `test_api.py:144` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:134-136`; `db.py:63-65` `WHERE author = ? COLLATE NOCASE`; `test_api.py:152` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `app.py:143` `_get_book`; `test_api.py:183`,`191` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:149` `_update_book`; `db.py:77`; `test_api.py:200` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:159` `_delete_book`; `db.py:91`; `test_api.py:259` |
| R7 | Data stored in SQLite | ✓ implemented | `db.py:5,37` `sqlite3.connect`; persistence-across-restart `test_server.py:92` |
| R8 | JSON responses + status codes | ✓ implemented | `app.py:19-29` status map, `app.py:81` json body; 201/200/204/400/404/405/413/503 exercised |
| R9 | title & author required | ✓ implemented | `validation.py:34-45`; `test_api.py:70-94` parametrized rejections |
| R10 | GET /health | ✓ implemented | `app.py:125` `_health` (pings DB, 503 on failure); `test_api.py:12` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run, options table, Test, API sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 70 tests collected across `test_api.py` (66) + `test_server.py` (4) |

No missing or partial requirements. Beyond-spec enhancements are logged as info findings, not deductions.

## Build & Test

Not re-run — scores read from `scores.json` (inline gate; row not yet in `retort.db`):

```text
scores.json: test_coverage=0.97  defect_rate=1.0  code_quality=0.833
             maintainability=0.901  idiomatic=0.88  token_efficiency=0.040
```

```text
python3 -m pytest --collect-only -q
tests/test_api.py: 66
tests/test_server.py: 4
-> 70 tests, 0 skipped   (test_coverage=0.97 + defect_rate=1.0 => all pass)
```

Service uses only the Python standard library (`wsgiref`, `sqlite3`); there is no compile step, so build == import + test success.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, `books_api/`) | 440 |
| Lines of code (incl. tests) | 971 |
| Files (source + tests) | 8 |
| Dependencies (runtime) | 0 (std-lib only) |
| Dependencies (dev) | 2 (pytest, pytest-cov) |
| Tests total / effective | 70 / 70 |
| Skip ratio | 0% |
| Build duration | n/a (std-lib, no build) |

## Findings

Top items (full list in `findings.jsonl`) — all info-level, all beyond-spec quality, no deductions:

1. [info] Validation goes well beyond the spec (year range, type-strict, length caps) — `validation.py:47-63`
2. [info] Thread-safe locked SQLite connection + threading WSGI server; concurrency test — `db.py:36-40`, `test_server.py:75`
3. [info] Health check verifies DB reachability, returns 503 on failure — `app.py:125-131`
4. [info] Hardened routing: 405 Allow header, 413 oversized body, JSON 500, SQL-injection test — `app.py`, `test_api.py:173`

## Architecture

`run-summary` skill not available in this session. Module map:

- `books_api/app.py` — WSGI `BooksApp`; regex routing, `HTTPError`→JSON mapping, request body parsing/limits.
- `books_api/db.py` — `BookRepository`; lock-guarded shared SQLite connection, full CRUD.
- `books_api/validation.py` — `validate_book`; required/optional field checks, error aggregation.
- `books_api/__main__.py` — CLI (`--host/--port/--db` + env), `ThreadingWSGIServer`.
- `tests/` — `conftest.py` in-process WSGI client; `test_api.py` (66) integration; `test_server.py` (4) real-socket + persistence + CLI.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=high_language=python_model=claude-opus-5-5_prompt=neutral/rep3
cat scores.json
grep -rnE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l   # 0
python3 -m pytest --collect-only -q | tail -3                                        # 70 tests
find books_api -name '*.py' | xargs wc -l | tail -1                                  # 440 source LOC
```
