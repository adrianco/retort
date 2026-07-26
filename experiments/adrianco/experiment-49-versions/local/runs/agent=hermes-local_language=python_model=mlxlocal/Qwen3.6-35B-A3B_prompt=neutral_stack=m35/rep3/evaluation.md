# Evaluation: hermes-local · python · Qwen3.6-35B-A3B · prompt=neutral · stack=m35 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective)
- **Build:** pass — Flask app imports and constructs via `create_app` (defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.79 from scores.json
- **Architecture:** single-module Flask app-factory; `run-summary` skill unavailable (not registered) — described inline below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:59` create_book; persists 4 fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:94` list_books; `SELECT * FROM books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:100-104` `WHERE author LIKE ?`; test `test_list_books_filter_by_author` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:111` get_book; 404 at :117 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:121` update_book; UPDATE at :145 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:155` delete_book; DELETE at :163 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,27` sqlite3, `CREATE TABLE books` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | jsonify + 201/200/404/400 throughout `app.py` |
| R9 | Input validation: title & author required | ✓ implemented | `app.py:71-75` (create) and `:139-143` (update) reject empty → 400 |
| R10 | GET /health health-check | ✓ implemented | `app.py:55` health_check → `{'status':'healthy'}`, 200 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — install, run, endpoints, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 14 tests in `test_app.py`; test_coverage=0.96 |

No prompt-factor requirements (`prompt=neutral` adds no extra checkable instructions).

## Build & Test

Scores read from `scores.json` (inline gate output) — not re-run per skill guidance:

```text
test_coverage = 0.96   (build + tests execute; 96% line coverage)
defect_rate   = 1.0    (build + tests pass)
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.8
```

Test suite (`test_app.py`, 14 tests, 0 skips): health, create (success + missing title +
missing author + no body), list (empty + after-create + author filter), get (found + 404),
update (success + 404), delete (success + 404). Each test uses an isolated temp SQLite DB.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 176 |
| Lines of code (test_app.py) | 234 |
| Files (source, excl. artifacts/logs) | app.py, test_app.py, requirements.txt, README.md |
| Dependencies | 2 (flask>=3.0, pytest>=7.0) |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| API calls / tokens | 18 calls, 62.6K non-cache tokens (44.5K in / 18.2K out) |

## Architecture (run-summary skill unavailable)

Single-module Flask application using the app-factory pattern (`create_app`). Per-request
SQLite connection stored on `g` with WAL journal mode; `init_db` creates the `books` table
(id autoincrement, title/author NOT NULL, year, isbn). Six routes plus `/health`, all
returning JSON with correct status codes. Tests inject a temp-file DB via `test_config`,
giving full isolation per test. Clean separation of connection lifecycle, schema init, and
routing; no over-engineering.

## Findings

Full list in `findings.jsonl`:

1. [low] Production entrypoint runs Flask with `debug=True` bound to `0.0.0.0` (`app.py:176`)
2. [info] Author filter uses SQL `LIKE` substring match rather than exact equality (`app.py:102`) — a benign superset of the spec

No high/critical findings. This is a complete, passing implementation of the spec.

## Reproduce

```bash
cd "runs/agent=hermes-local_language=python_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35/rep3"
cat scores.json                      # stored build/test/quality scores
grep -cE "def test_" test_app.py     # 14
grep -rEc "pytest\.skip|xfail" test_app.py  # 0
python -m pytest test_app.py -v      # optional re-run (scores already stored)
```
