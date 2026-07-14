# Evaluation: agent=hermes-local language=python prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local (model qwen3-coder-30b), framework=Flask, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — `test_coverage=0.53` from `scores.json` (>0 ⇒ tests executed)
- **Build:** pass — import/collection succeeded (`defect_rate=1.0`, `test_coverage=0.53` from `scores.json`; not re-run)
- **Lint:** pass — `code_quality=0.833` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 2 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:35-65` create_book, INSERT + 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:68-83` get_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:73-76` `WHERE author LIKE ?` (substring) |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:86-97`, 404 at :95 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:100-139`, 404/400 guards |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:142-159`, 404 guard |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:8-27` sqlite3 + `books.db` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201/200/404/400 via `jsonify` throughout |
| R9 | Input validation: title & author required | ✓ implemented | `app.py:40` (POST), `app.py:116` (PUT) → 400 |
| R10 | GET /health health check | ✓ implemented | `app.py:30-32` returns `{status:'healthy'}` 200 |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` (setup, endpoints, curl examples) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test_app.py` — 11 `test_*` methods; `test_coverage=0.53>0` |

## Build & Test

Not re-run (per skill: stored scores stand in). From `scores.json`:

```text
test_coverage = 0.53   # tests executed, ~53% line coverage
defect_rate   = 1.0    # build + tests succeeded
code_quality  = 0.833
maintainability = 0.993
idiomatic     = 0.58
token_efficiency = 0.020
```

Test suite (`test_app.py`, imports `app.py`): 11 methods covering health, create, create-missing-field (400), list, list-by-author, get-by-id, get-missing (404), update, update-missing (404), delete, delete-missing (404). 0 skips.

Note: `_agent_stdout.log` records the agent could not run tests itself and could not overwrite the scaffold files, so it emitted `app_modified.py` / `test_app_fixed.py` variants. The retort scorer nonetheless ran `test_app.py` against `app.py` successfully.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 163 |
| Lines of code (test_app.py) | 222 |
| Source files (incl. duplicates) | app.py, app_modified.py, test_app.py, test_app_fixed.py |
| Dependencies | 1 (Flask==2.3.3) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Line coverage | 53% |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [medium] Two divergent copies of the app and test suite ship in the workspace (`app.py` vs `app_modified.py`, `test_app.py` vs `test_app_fixed.py`) — canonical deliverable is ambiguous.
2. [medium] Flask runs with `debug=True` bound to `0.0.0.0` (`app.py:163`) — Werkzeug debugger RCE risk if deployed.
3. [low] Build artifacts (`books.db`, `.coverage`) committed into the workspace.
4. [info] `?author=` filter uses substring `LIKE` match rather than exact match (`app.py:76`).

No critical or high findings: the run is functionally complete and all 12 pinned requirements are implemented with passing tests.

## Reproduce

```bash
cd experiment-17-hermes/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep1
cat scores.json                     # stored mechanical scores (build/test/lint)
python -m pytest test_app.py -v     # optional: re-run the 11 tests against app.py
grep -n "debug=True" app.py app_modified.py
diff app.py app_modified.py         # only the listen port differs
```
