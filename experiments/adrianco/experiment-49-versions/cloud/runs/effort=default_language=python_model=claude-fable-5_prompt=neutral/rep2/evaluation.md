# Evaluation: effort=default_language=python_model=claude-fable-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-fable-5, prompt=neutral, effort=default (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective)
- **Build:** pass — test_coverage=0.96, defect_rate=1.0 from `scores.json`
- **Lint:** pass — code_quality=0.79 from `scores.json`
- **Architecture:** run-summary skill unavailable; single-module Flask app (`app.py`) with an application factory.
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Checklist from the pinned `cloud/REQUIREMENTS.json` (constant denominator, 12 items).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:90` `create_book` INSERTs all four fields; `test_create_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:108` `list_books` returns full collection; `test_list_books_and_author_filter` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:112-115` filters by `author` query param; `test_list_books_and_author_filter` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:120` `get_book`, 404 at `:124`; `test_get_single_book`, `test_get_missing_book_returns_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:127` `update_book` (partial update); `test_update_book` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:152` `delete_book`, 204/404; `test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:10-39` `sqlite3`, `CREATE TABLE books`, file-backed `books.db` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404/405 returned |
| R9 | Validation: title and author required | ✓ implemented | `app.py:50-84` `validate_payload`; `test_create_book_validation_errors` |
| R10 | GET /health | ✓ implemented | `app.py:86-88` returns `{"status":"ok"}`; `test_health` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — setup, run, test, endpoint table, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 9 test functions in `test_app.py`; test_coverage=0.96 |

No prompt-factor requirements: `prompts/neutral.md` prescribes no methodology (P-list empty).

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.96   → build + tests executed and passed
defect_rate   = 1.0    → build+test succeeded
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.62
```

```text
pytest: 9 tests, 0 skips (grep for pytest.skip/xfail = 0)
Covers health, create, optional-field defaults, validation errors,
list+author filter, get, 404, update (+validation+404), delete (+404).
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 301 (app.py 175 + test_app.py 126) |
| Files | 11 (incl. artifacts: .coverage, books cache) — 4 source/doc: app.py, test_app.py, README.md, requirements.txt |
| Dependencies | 2 (flask, pytest) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores.json) |

## Findings

Full list in `findings.jsonl`. All are info-level — no requirement gaps, build/test failures, or skipped tests.

1. [info] SQLite connection not concurrency-hardened (fine for single-worker dev server) — enhancement only
2. [info] ISBN has no UNIQUE constraint — enhancement, not required by spec
3. [info] test_coverage 0.96 — the `__main__` app.run() guard is uncovered (conventional)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=default_language=python_model=claude-fable-5_prompt=neutral/rep2
cat scores.json                 # stored mechanical scores (not re-run)
grep -rE "pytest\.skip|xfail" . --include="*.py" | wc -l   # 0 skips
grep -cE "^def test_" test_app.py                          # 9 tests
# to actually run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python3 -m pytest -v
```
