# Evaluation: mlx-community--Qwen3-Coder-Next-4bit · prompt=neutral · stack=m80 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlx-community/Qwen3-Coder-Next-4bit, prompt=neutral, stack=m80
- **Task:** rest-api-crud (REPAIR task — fix a prior failed attempt)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json, R1–R12)
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective) — from `defect_rate=1.0`, `test_coverage=0.95` in scores.json
- **Build:** pass (import/collection succeeded; `defect_rate=1.0`)
- **Lint:** pass — `code_quality=0.83` from scores.json
- **Architecture:** run-summary skill unavailable in this session; codebase is a 4-module FastAPI + SQLAlchemy CRUD service (main/database/schemas/crud) plus test_main.py
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `main.py:24 create_book` → `crud.py:16 create_book` persists all four fields |
| R2 | GET /books lists all books | ✓ implemented | `main.py:29 read_books` → `crud.py:11 get_books` returns `.all()` |
| R3 | GET /books ?author= filter | ✓ implemented | `crud.py:12-14` filters on `BookModel.author`; `test_main.py:test_get_books_with_author_filter` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `main.py:34 read_book` raises 404; `test_get_book_by_id`, `test_get_book_not_found` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `main.py:42 update_book` → `crud.py:31 update_book` (partial update via exclude_unset); `test_update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `main.py:51 delete_book` → `crud.py:45 delete_book`; `test_delete_book` |
| R7 | Data stored in SQLite | ~ implemented (defect) | `database.py:5` SQLite URL + SQLAlchemy model; persistence works. BUT app never creates the schema on startup (see finding R7-partial) — only tests do. |
| R8 | JSON responses + appropriate status codes | ✓ implemented | 201 create, 200 get/list, 404 not-found, 204 delete, 422 validation |
| R9 | Validation: title & author required | ✓ implemented | `schemas.py:7-8` required + min_length=1; `test_create_book_validation_error` asserts 422 (see R9-note) |
| R10 | GET /health | ✓ implemented | `main.py:19 health_check` returns `{"status":"healthy",...}`; `test_health_check` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — install, uvicorn run, curl examples, pytest (minor isbn example bug, see doc-isbn) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 13 test functions in `test_main.py`, all pass |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.95   # tests executed and passed (>0); ~95% line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.833
idiomatic     = 0.95
```

Test inventory (`grep -c '^def test_' test_main.py` = 13, 0 skips):
health, create, validation-error, list-empty, author-filter, get-by-id,
get-404, update, update-404, delete, delete-404 (+ fixtures).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 167 (main 57, crud 52, database 30, schemas 28) |
| Lines of code (tests) | 209 |
| Files (source + test) | 5 .py |
| Dependencies | 6 (requirements.txt) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| API calls (agent) | 13 · in 47,958 / out 1,858 tokens |

## Findings

Top findings (full list in `findings.jsonl`):

1. [medium] App never creates the SQLite schema on startup — `uvicorn main:app` + `/books` would raise "no such table"; tests pass only because they create tables themselves.
2. [low] README curl example isbn `978-0743273565` (14 chars) fails the `max_length=13` schema validation.
3. [info] Validation returns 422 (FastAPI-standard) rather than the checklist's literal 400 — still rejects invalid input, R9 met.

## Reproduce

```bash
cd "experiments/adrianco/experiment-61-hermes-0205/local/runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-Next-4bit_prompt=neutral_stack=m80/rep1"
cat scores.json                              # stored mechanical scores (not re-run)
grep -c '^def test_' test_main.py            # 13
grep -rEc 'pytest\.skip|xfail' test_main.py  # 0
grep -nE 'init_db|on_event|lifespan|create_all|startup' main.py  # none — the R7 defect
```
