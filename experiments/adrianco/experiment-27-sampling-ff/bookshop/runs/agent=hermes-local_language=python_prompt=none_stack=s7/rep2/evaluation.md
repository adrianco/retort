# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s7 · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), prompt=none, stack=s7, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — from `scores.json` test_coverage=0.95, defect_rate=1.0 (build+test succeeded; not re-run)
- **Lint:** pass — code_quality=0.79 from `scores.json`
- **Architecture:** single-module Flask app; `run-summary` skill unavailable in this session (skipped)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:64 create_book` — inserts all four fields, 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:99 list_books` → `SELECT * FROM books` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:105-108` LIKE filter; `test_app.py:113 test_filter_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:115 get_book`; `test_app.py:140 test_get_nonexistent_book` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:125 update_book`; `test_app.py:151 test_update_book_success` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:164 delete_book`; `test_app.py:175` verifies it is gone |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:3,15,29-44` sqlite3, `books.db`, schema init |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify(...)` with 201/200/404/400 throughout `app.py` |
| R9 | Validation: title and author required | ✓ implemented | `app.py:74-77`; `test_app.py:73,81` missing-title/author → 400 |
| R10 | GET /health health check | ✓ implemented | `app.py:58 health` → `{"status":"ok"}`, 200 |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — install, run, endpoints, tests |
| R12 | At least 3 unit/integration tests | ✓ implemented | `test_app.py` — 12 tests; test_coverage=0.95 (>0) |

## Build & Test

Build/test were **not re-run** — mechanical scores read from `scores.json`:

```text
scores.json: test_coverage=0.95  defect_rate=1.0  code_quality=0.79
             maintainability=1.0  idiomatic=0.72  token_efficiency=0.0178
# test_coverage=0.95 ⇒ build + all 12 tests passed (95% line coverage)
# defect_rate=1.0    ⇒ build+test succeeded
```

```text
pytest (per agent stdout): 12/12 passed, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py, source only) | 179 |
| Lines of code (incl. test_app.py) | 372 |
| Files (source, excl. artifacts) | 4 (app.py, test_app.py, README.md, requirements.txt) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Full list in `findings.jsonl` (none at high/critical):

1. [low] app runs with `debug=True` bound to `0.0.0.0` — `app.py:179`
2. [low] test_coverage=0.95 — 400/validation error branches unexercised
3. [info] author filter is a substring LIKE match, not exact — `app.py:107`

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s7/rep2
cat scores.json                       # stored mechanical scores (build/test/lint)
grep -cE "def test_" test_app.py      # 12
grep -rEn "pytest\.skip|xfail" .      # 0 skips
python -m pytest test_app.py -v       # (optional) 12 passed
```
