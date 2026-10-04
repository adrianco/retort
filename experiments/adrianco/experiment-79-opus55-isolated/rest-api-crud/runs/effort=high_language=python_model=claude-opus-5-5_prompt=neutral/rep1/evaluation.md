# Evaluation: rest-api-crud effort=high language=python model=claude-opus-5-5 prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=high
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 62 passed / 0 failed / 0 skipped (62 effective)
- **Build:** pass — from `scores.json` (`defect_rate=1.0`; stdlib-only, no build step)
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Stored scores (`scores.json`): test_coverage=0.95, defect_rate=1.0, code_quality=0.83,
maintainability=0.91, idiomatic=0.87, token_efficiency=0.05. Tests executed and all
passed (test_coverage=0.95 is line coverage, not a pass-rate zero); the run clears the
test gate.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `bookapi/app.py:create_book` → `store.py:create`; `tests/test_api.py:test_create_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:list_books` → `store.py:list`; `test_api.py:test_list_books_returns_all_in_creation_order` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:list_books` reads `author` query; `store.py:list` `WHERE author = ?`; `test_api.py:test_list_books_filters_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:get_book` raises `_not_found`; `test_api.py:test_get_book`, `test_get_missing_book` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:update_book` → `store.py:update`; `test_api.py:test_update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:delete_book` → `store.py:delete`; `test_api.py:test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `bookapi/store.py` uses `sqlite3`, `AUTOINCREMENT` schema; `test_server.py:test_books_persist_across_restarts` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:__call__` sets `Content-Type: application/json`; 201/200/204/400/404/405/413/500 all present |
| R9 | Validation: title and author required | ✓ implemented | `bookapi/validation.py:_required_text`; `test_api.py:test_create_rejects_invalid_fields` (400) |
| R10 | GET /health health check | ✓ implemented | `app.py:health` (pings DB, 503 on failure); `test_api.py:test_health` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Setup / Run / curl examples / project layout |
| R12 | At least 3 unit/integration tests | ✓ implemented | 62 tests across `tests/test_api.py`, `tests/test_server.py` |

No requirement is missing or partial. Enhancements beyond spec (not deductions): HEAD
support, `Allow` header on 405, 413 for oversized bodies, lone-surrogate rejection,
SQL-injection-safe parameterized queries, and a concurrency test over a real socket.

## Build & Test

Not re-run — stored scores read from `scores.json` per the evaluate-run skill
(re-running the toolchain is pure duplication).

```text
scores.json: {"test_coverage": 0.95, "defect_rate": 1.0, "code_quality": 0.833,
              "maintainability": 0.914, "idiomatic": 0.87}
defect_rate=1.0 ⇒ build+test succeeded. test_coverage=0.95 ⇒ 95% line coverage.
```

```text
pytest --collect-only: 62 tests collected (0 skipped)
grep for skips (pytest.skip / @pytest.mark.skip / xfail): 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, `bookapi/*.py`) | 397 |
| Lines of code (tests) | 460 |
| Files (source + tests) | 8 |
| Dependencies | 1 (pytest, dev-only; 0 runtime) |
| Tests total | 62 |
| Tests effective | 62 |
| Skip ratio | 0% |
| Build duration | n/a (stdlib, no build step) |

## Findings

All 3 findings are `info` (enhancements / notes); there are no defects. Full list in
`findings.jsonl`:

1. [info] E1 — Robustness well beyond spec (HEAD, 405 `Allow`, 413, surrogate/SQL-injection guards)
2. [info] E2 — Stdlib-only implementation (wsgiref + sqlite3), zero runtime dependencies
3. [info] COV1 — Line coverage 0.95; the `__main__` serve loop is the likely uncovered path

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=high_language=python_model=claude-opus-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored build/test/lint scores
python3 -m pytest --collect-only -q tests/        # 62 tests, 0 skipped
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/   # 0 skips
wc -l bookapi/*.py tests/*.py                      # LOC
```
