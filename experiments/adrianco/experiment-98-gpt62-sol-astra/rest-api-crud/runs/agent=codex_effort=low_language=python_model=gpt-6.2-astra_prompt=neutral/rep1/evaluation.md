# Evaluation: agent=codex effort=low language=python model=gpt-6.2-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=gpt-6.2-astra, agent=codex, effort=low, prompt=neutral, framework=unknown (stdlib)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass — `compileall` + `unittest` succeeded (test_coverage=0.9, defect_rate=1.0 from scores.json)
- **Lint:** pass — code_quality=0.7889 from scores.json
- **Architecture:** single-module stdlib WSGI app; run-summary skill unavailable (not in this harness) — summarized inline below
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

The neutral prompt factor (`prompts/neutral.md`) prescribes no methodology and adds no
checkable requirements, so the `P*` list is empty; TASK.md (pinned to R1–R12) is the whole spec.

## Requirements

Denominator fixed by `rest-api-crud/REQUIREMENTS.json` (12 requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:85-89` INSERT + Location header |
| R2 | GET /books lists all books | ✓ implemented | `app.py:78-79` SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:73-76` WHERE author=?; `test_app.py:46` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:97-100` SELECT by id, else 404 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:91-92` UPDATE; 404 when row absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:94-95` DELETE, rowcount-gated |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:5,43,48-50` sqlite3 + CREATE TABLE |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:108-110` json.dumps; 201/200/400/404/405/415/503 |
| R9 | Validation: title and author required | ✓ implemented | `app.py:24-27` nonempty-string check → 400; `test_app.py:49-52` |
| R10 | GET /health health check | ✓ implemented | `app.py:56,68-70` DB ping → {"status":"ok"}; `test_app.py:55` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` run cmd, env vars, endpoint table, curl example |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` 4 tests, all pass |

## Build & Test

```text
venv/bin/python -m compileall -q app.py test_app.py && venv/bin/python -m unittest -v
test_health ... ok
test_lifecycle_and_persistence ... ok
test_listing ... ok
test_validation ... ok
----------------------------------------------------------------------
Ran 4 tests in 0.005s
OK
```

(Scores read from `scores.json`, not re-run: test_coverage=0.9, defect_rate=1.0, code_quality=0.7889.)

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 175 (app.py 119, test_app.py 56) |
| Files (.py) | 2 |
| Dependencies | 0 (Python standard library only) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build/test | pass |

## Architecture (inline — run-summary skill unavailable)

Single module `app.py`. `create_app(path)` is a factory returning a WSGI `application`; it
creates the `books` table on init and closes over a per-request `connect()`. `route()` dispatches
on `PATH_INFO`/`REQUEST_METHOD` with method allow-lists (405 + Allow header on mismatch).
`read_book()` isolates body parsing and validation (content-type 415, size cap, type checks).
DB errors map to 503. Tests drive the app directly through the WSGI callable with a temp SQLite
file, covering CRUD lifecycle, cross-restart persistence, author filtering, validation, and health.

## Findings

Top findings (full list in `findings.jsonl`) — none at/above `high`:

1. [info] Returns 415 for non-JSON content type beyond spec (`app.py:13`)
2. [info] Maps sqlite3.Error to 503; emits Allow header on 405 (`app.py:106-107`, `app.py:65`)

No requirement is missing or partial; no tests are skipped or disabled; build and tests pass.

## Reproduce

```bash
cd "experiments/adrianco/experiment-98-gpt62-sol-astra/rest-api-crud/runs/agent=codex_effort=low_language=python_model=gpt-6.2-astra_prompt=neutral/rep1"
cat scores.json                               # stored mechanical scores (no re-run)
grep -rE "skip|xfail" --include="*.py" .      # 0 skips
venv/bin/python -m unittest -v                # optional: 4 tests, OK
```
