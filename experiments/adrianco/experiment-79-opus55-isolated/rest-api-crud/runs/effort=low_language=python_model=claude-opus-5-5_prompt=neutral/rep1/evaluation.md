# Evaluation: rest-api-crud · effort=low language=python model=claude-opus-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** pass (test_coverage=0.91 from `scores.json`) / 0 skipped — 12 test functions, one parametrized into 7 cases (~18 effective checks)
- **Build:** pass — from `scores.json` (defect_rate=1.0 ⇒ build+test succeeded); not re-run
- **Lint:** pass — code_quality=0.79 from `scores.json`
- **Architecture:** single-module stdlib service (`app.py`) + test suite (`test_app.py`); summarized inline below (run-summary not invoked for a 2-file, 376-line codebase)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:176-178` POST branch → `store.create` (`app.py:84-90`) |
| R2 | GET /books lists all books | ✓ implemented | `app.py:173-175` → `store.list` (`app.py:92-98`) |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:174` reads `author` query param; `app.py:95` `WHERE author = ? COLLATE NOCASE`; `test_list_and_author_filter` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.py:184-196`; 404 at `app.py:194-195`; `test_create_and_get`, `test_not_found_and_method_not_allowed` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:186-187` → `store.update` (`app.py:105-111`); `test_update` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:188-191` → `store.delete` (`app.py:113-116`); `test_delete` |
| R7 | Data stored in SQLite | ✓ implemented | `sqlite3` throughout; `init_db` (`app.py:31-43`); `test_data_persists_across_restart` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `_send` (`app.py:126-133`); 201/200/204/400/404/405/413/500 across `_route` |
| R9 | Validation: title and author required | ✓ implemented | `validate_book` (`app.py:46-74`); `test_create_validation` (7 cases) |
| R10 | GET /health health check | ✓ implemented | `app.py:167-170` returns `{"status": "ok"}`; `test_health` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — Run/Test/API/Example sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` — 12 test functions; test_coverage=0.91 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill Step 2):

```text
scores.json:
  test_coverage   = 0.91   (build + tests passed; >0 ⇒ tests executed)
  defect_rate     = 1.0    (build + test succeeded)
  code_quality    = 0.7889 (lint/quality)
  maintainability = 1.0
  idiomatic       = 0.88
```

Skip scan (`grep -E "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py`): 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 238 |
| Lines of code (test_app.py) | 138 |
| Files (excl. artifacts) | app.py, test_app.py, README.md, requirements-dev.txt, TASK.md, stack.json |
| Dependencies | 1 dev (`pytest`); runtime = stdlib only |
| Test functions | 12 (one parametrized ×7 → ~18 effective) |
| Skipped tests | 0 |
| Skip ratio | 0% |

## Architecture (inline)

- `app.py` — one module, no third-party runtime deps. `ApiError` (typed HTTP errors) → `validate_book` (input validation) → `BookStore` (SQLite persistence, connection-per-op for thread safety) → `BookHandler` (`BaseHTTPRequestHandler` routing via regex `BOOK_PATH` and a `_route`/`_dispatch` pair) → `make_server`/`main` (env-configured `ThreadingHTTPServer`).
- `test_app.py` — spins up the real server on an ephemeral port with a `tmp_path` SQLite file; exercises health, CRUD, author filter, validation, bad-JSON, not-found/method-not-allowed, persistence, and unit-level `validate_book`.

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no defects:

1. [info] Thread-safe SQLite via connection-per-operation (`app.py:77-116`)
2. [info] Robust request hardening beyond spec — 1MB body cap, bool-year rejection, 500 fallback
3. [info] Case-insensitive author filter (`app.py:95`)

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=python_model=claude-opus-5-5_prompt=neutral/rep1"
cat scores.json                       # stored mechanical scores (build/test/lint)
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # skip scan
# optional re-run: python3 -m pytest
```
