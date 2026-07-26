# Evaluation: m35 · hermes-local · Qwen3.6-35B-A3B · prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 17 passed / 0 failed / 0 skipped (17 effective)
- **Build:** pass — from `scores.json` `test_coverage=0.97`, `defect_rate=1.0` (tests executed and passed)
- **Lint:** pass — `code_quality=0.79` (from `scores.json`)
- **Architecture:** single-module Flask app (`app.py`) + pytest suite (`test_app.py`); see below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

All requirements from the pinned `REQUIREMENTS.json` (constant 12-item denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:60-105` `create_book`; `test_app.py:49` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:110-124` `list_books`; `test_app.py:114` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:116-119` `LIKE %author%`; `test_app.py:123` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:129-136` `get_book`; `test_app.py:139,148` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:141-191` `update_book`; `test_app.py:157` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:196-206` `delete_book`; `test_app.py:183` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,27-42` `sqlite3` + `books` table |
| R8 | JSON responses with correct HTTP codes | ✓ implemented | `jsonify(...)` with 200/201/400/404 throughout `app.py` |
| R9 | Validation: title and author required | ✓ implemented | `app.py:79-82` returns 400; `test_app.py:75,83,91` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:52-55` `health`; `test_app.py:38` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — setup, run, curl examples, testing |
| R12 | ≥3 unit/integration tests | ✓ implemented | 17 tests in `test_app.py` (`grep -c def test_` = 17) |

No requirements partial or missing. No enhancements beyond spec beyond a substring author filter (see findings).

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.97   # tests executed and passed (17/17); ~3% lines uncovered
defect_rate   = 1.0    # build + tests succeeded
code_quality  = 0.7889
maintainability = 0.9938
idiomatic     = 0.78
```

Agent's own report (`_agent_stdout.log`): "All 17 tests pass."
Skip scan: `grep -Ec "pytest.skip|@pytest.mark.skip|xfail" test_app.py` = 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 410 (app.py 213 + test_app.py 197) |
| Files (workspace, ex. artifacts) | app.py, test_app.py, requirements.txt, README.md |
| Dependencies | 2 (flask>=3.0, pytest>=8.0) |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Output tokens | 5,508 (8 API calls; `.hermes_usage.json`) |

## Findings

Full list in `findings.jsonl`:

1. [low] App runs with `debug=True` and binds `0.0.0.0` (`app.py:213`) — Werkzeug debugger RCE risk if exposed.
2. [info] `test_coverage=0.97`, not 1.0 — malformed-JSON-body and PUT invalid-year branches uncovered.
3. [info] `?author=` filter is substring (`LIKE %x%`), not exact match — reasonable and tested.

No critical, high, or medium findings — a clean, spec-complete run.

## Architecture

Two-file Flask service. `app.py`: per-request SQLite connection via Flask `g` with `teardown_appcontext` cleanup and WAL mode; `init_db()` creates the `books` table idempotently at import time; six routes + `/health`, all returning `jsonify` with explicit status codes; input validation strips/rejects empty title/author and coerces `year`. `test_app.py`: pytest with a `client` fixture that swaps `DATABASE` to a temp file per session, 17 tests across health/create/list/get/update/delete including 404 and 400 paths. (`run-summary` not invoked — codebase is small enough to describe inline.)

## Reproduce

```bash
cd runs/agent=hermes-local_language=python_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35/rep2
cat scores.json                                              # stored build/test/lint scores
grep -c "def test_" test_app.py                              # 17
grep -Ec "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py # 0
wc -l app.py test_app.py                                     # LOC
```
