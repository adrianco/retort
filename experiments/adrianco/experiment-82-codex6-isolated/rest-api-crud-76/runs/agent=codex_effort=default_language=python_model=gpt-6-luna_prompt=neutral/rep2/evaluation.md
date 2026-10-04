# Evaluation: agent=codex effort=default language=python model=gpt-6-luna prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=gpt-6-luna, agent=codex, prompt=neutral, effort=default, framework=unknown (stdlib WSGI)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned checklist `REQUIREMENTS.json`, R1–R12)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — `defect_rate=1.0` (scores.json); import/compile clean (`py_compile` ok in agent log)
- **Lint:** pass — `code_quality=0.7889` (scores.json)
- **Architecture:** summary skill not run (`run-summary` not registered this session); inline note below
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

Scores (from `scores.json`, the inline gate output — DB row not yet present for this isolated re-run):
`test_coverage=0.9`, `defect_rate=1.0`, `code_quality=0.7889`, `maintainability=0.9275`, `idiomatic=0.68`, `token_efficiency=0.0327`.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:114` `_create`, INSERT `app.py:120-123`; test `test_app.py:40` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:127` `_list`, `SELECT * ... ORDER BY id` `app.py:131`; test `test_app.py:58` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:128,132-133` author-filtered query; test `test_app.py:59-60` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:136` `_get`, 404 `app.py:139-140`; tests `test_app.py:44,66` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:143` `_update`, UPDATE `app.py:152-154`; test `test_app.py:46` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:159` `_delete`, 404 on miss `app.py:162-163`; test `test_app.py:51` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:20-32` `_connect` uses `sqlite3`, persistent file `books.db` `app.py:16` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:170-177` `_respond` (JSON + `HTTPStatus`); 201/200/204/400/404/405/500 used throughout |
| R9 | Validation: title and author required | ✓ implemented | `app.py:43-45` missing-field check; test `test_app.py:63-64` (400) |
| R10 | GET /health endpoint | ✓ implemented | `app.py:82-83` returns `{"status":"ok"}`; test `test_app.py:65` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md:1-35` (run, endpoints, tests) |
| R12 | At least 3 unit/integration tests | ✓ implemented | 4 tests in `test_app.py`; `test_coverage=0.9 > 0` |

## Build & Test

```text
python -m unittest -v   (from agent log, item_9)
test_create_get_update_and_delete_book ... ok
test_invalid_json_is_reported ... ok
test_list_and_author_filter ... ok
test_validation_health_and_missing_book ... ok
----------------------------------------------------------------------
Ran 4 tests in 0.005s
OK
python -m py_compile app.py test_app.py   (clean)
```

Build/test not re-run here — stored scores used: `test_coverage=0.9`, `defect_rate=1.0` (scores.json). 0 skipped tests (grep for `unittest.skip`/`pytest.skip`/`xfail` = 0).

## Architecture (inline — `run-summary` not run)

Single-module WSGI app (`app.py`, 187 LOC), zero third-party deps. `BookAPI.__call__`
dispatches by method+path (`/health`, `/books`, `/books/{id}` via regex). Persistence is a
per-request SQLite connection (`_connect`) with a `CREATE TABLE IF NOT EXISTS` bootstrap;
row→dict via `_book`. Validation centralised in `_validate` (required fields, type checks,
unknown-field rejection). Responses funnel through one `_respond` helper (JSON body,
Content-Length, optional extra headers). Tests (`test_app.py`) drive the WSGI callable
directly with a synthetic `environ`, each using a temp-dir SQLite file.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 265 (app.py 187, test_app.py 78) |
| Files (excl. .git/__pycache__) | 11 (incl. venv/db artifacts) |
| Dependencies | 0 (stdlib only — no requirements.txt/pyproject.toml) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build/test duration | ~0.005s (unittest, per agent log) |

## Findings

Full list in `findings.jsonl` (no critical/high/medium):

1. [low] Coverage 0.9 — DB-error 500 path (`app.py:101-102`) and `__main__` server bootstrap (`app.py:183-187`) untested
2. [info] Validation exceeds spec — rejects unknown fields and non-integer year (`app.py:56-65`)
3. [info] POST returns a `Location` header with 201 (`app.py:125`)
4. [info] PUT uses documented full-replace semantics (`app.py:145`, `README.md:25`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-76/runs/agent=codex_effort=default_language=python_model=gpt-6-luna_prompt=neutral/rep2"
cat scores.json                                   # stored mechanical scores
grep -rEn "unittest\.skip|pytest\.skip|xfail" . --include="*.py" | wc -l   # 0 skips
python -m unittest -v                             # re-run tests (optional; 4 ok)
```
