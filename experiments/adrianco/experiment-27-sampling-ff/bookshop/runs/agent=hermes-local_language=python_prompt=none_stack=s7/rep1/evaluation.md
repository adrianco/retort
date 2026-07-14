# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s7 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (Flask, inferred), prompt=none, stack=s7
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective) — from `test_coverage=0.98` (build + tests pass) and `_agent_stdout.log` "16/16 passed"
- **Build:** pass — `test_coverage=0.98` from `scores.json` (import + test gate succeeded)
- **Lint:** pass — `code_quality=0.79` from `scores.json` (no lint failures)
- **Architecture:** `run-summary` skill unavailable in this session; see inline notes below
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:60` `create_book`, INSERT at `app.py:94` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:104` `list_books` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:118` LIKE filter; test `test_list_books_filter_by_author` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:129` `get_book`, 404 at `app.py:141` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:146` `update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:195` `delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,13,27` sqlite3 + `books.db` |
| R8 | JSON responses w/ appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/404/400 returned |
| R9 | Validation: title and author required | ✓ implemented | `app.py:84-88`; tests `test_create_book_missing_title/author` |
| R10 | GET /health health-check | ✓ implemented | `app.py:54` `health_check` → 200 `{"status":"healthy"}` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — install, run, test, endpoints, examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 16 tests in `test_app.py`; `test_coverage=0.98` |

## Build & Test

Not re-run — stored scores used per skill (test gate is authoritative):

```text
scores.json: test_coverage=0.98  defect_rate=1.0  code_quality=0.79
             maintainability=0.99  idiomatic=0.58  token_efficiency=0.021
_agent_stdout.log: "Test results: 16/16 passed in 0.08 seconds."
```

`test_coverage=0.98` (≠ 0) ⇒ build/import succeeded and tests executed and passed.
Skip scan (`grep pytest.skip|xfail test_app.py`): 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 219 |
| Lines of code (test_app.py) | 294 |
| Files (source) | 3 (app.py, test_app.py, requirements.txt) + README.md |
| Dependencies | 2 (flask, pytest) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Coverage | 98% |

## Findings

Full list in `findings.jsonl`. All below `high` — no blocking issues.

1. [low] Stray `books.db` left in workspace — created by import-time `init_db()` (`app.py:216`)
2. [low] `init_db()` runs as an import-time side effect (`app.py:216`)
3. [low] Non-JSON POST/PUT bodies may raise 415 instead of the intended 400 (`app.py:76,169`, `get_json()` without `silent=True`)
4. [info] Coverage 98%, not 100% — defensive error branches unexercised

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s7/rep1
cat scores.json                         # stored mechanical scores (no re-run)
grep -rnE "pytest\.skip|xfail" test_app.py | wc -l   # 0 skips
pytest test_app.py -v                   # optional: 16 passed
```
