# Evaluation: agent=hermes-local language=python prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3-Coder-Next via Hermes), framework=Flask, prompt=neutral
- **Status:** ok (functional defect: DB not initialized at startup — see findings)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective) — from defect_rate=1.0, test_coverage=0.88 in scores.json
- **Build:** pass — from scores.json (defect_rate=1.0; not re-run)
- **Lint:** pass — code_quality=0.79 from scores.json (not re-run)
- **Architecture:** single-module Flask app (app.py) + SQLite; run-summary skill unavailable, so no `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 1 high, 0 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:116 create_book`, `test_app.py:76 test_create_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:85 list_books`, `test_app.py:69 test_list_books_empty` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:93-97`, `test_app.py:219 test_list_books_with_filter` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:159 get_book`, `test_app.py:128/133` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:183 update_book`, `test_app.py:153 test_update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:255 delete_book`, `test_app.py:191 test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:23 sqlite3.connect(DEFAULT_DATABASE)` file-backed |
| R8 | JSON responses + correct status codes | ✓ implemented | jsonify with 201/200/400/404 throughout `app.py` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:124-132`, `test_app.py:98 test_create_book_validation` |
| R10 | GET /health | ✓ implemented | `app.py:76 health_check`, `test_app.py:61 test_health_check` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` (install, run, env vars, endpoints, tests) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 12 tests in `test_app.py`, test_coverage=0.88 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.88   # tests executed and passed; 88% line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.79   # lint/quality
maintainability = 0.96
idiomatic     = 0.68
```

No skipped/xfail tests (`grep` of test_app.py returns 0). All 12 tests effective.

## Metrics

| Metric | Value |
|--------|-------|
| Lines (app.py) | 275 |
| Lines (test_app.py) | 248 |
| Files (excl. caches) | 13 (4 deliverables: app.py, test_app.py, README.md, requirements.txt) |
| Dependencies | 1 (flask>=2.0.0) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Tokens (total / output) | 1,049,764 / 17,993 across 31 API calls |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [high] `init_db()` never called — a freshly run service 500s on the first `/books` request because the `books` table is never created (`app.py:38` defined, never invoked; `__main__` only calls `app.run()`). Tests hide this by creating their own schema and monkey-patching `get_db`.
2. [low] Unused `import json` in `app.py:3`.
3. [low] `reset_db()`/`_testing_db` test hooks are dead code — tests bypass them by monkey-patching `get_db` directly.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-24-qwennext80b-cached/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep1
cat scores.json                       # stored build/test/lint scores (not re-run)
grep -n "init_db" app.py              # confirm init_db defined but never called
grep -cE "def test_" test_app.py      # 12 tests
grep -rEc "skip|xfail" test_app.py    # 0 skips
# Demonstrate the startup defect on a clean DB:
#   rm -f books.db && python3 app.py & curl localhost:5000/books   # -> 500 no such table: books
```
