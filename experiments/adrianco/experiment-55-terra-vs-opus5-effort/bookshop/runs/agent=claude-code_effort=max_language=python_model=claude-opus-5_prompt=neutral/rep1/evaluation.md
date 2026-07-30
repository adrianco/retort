# Evaluation: agent=claude-code_effort=max_language=python_model=claude-opus-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5, agent=claude-code, effort=max, prompt=neutral, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 53 passed / 0 failed / 0 skipped (53 effective) — from test_coverage=0.99, defect_rate=1.0
- **Build:** pass — from retort.db (test_coverage=0.99 ⇒ build + tests ran and passed)
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** run-summary skill unavailable; see notes below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `bookapi/routes.py:60 create_book` → `repository.py:78 create_book`; test `test_create_returns_201_with_location_and_stored_fields` |
| R2 | GET /books lists all books | ✓ implemented | `routes.py:72 list_books` → `repository.py:52 list_books`; test `test_list_returns_books_in_insertion_order` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `routes.py:76` reads `author`; `repository.py:62` WHERE author COLLATE NOCASE; test `test_filter_returns_only_that_authors_books` |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `routes.py:80 get_book`, `_book_or_404`; test `test_missing_book_returns_404_for_every_verb` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `routes.py:85 replace_book` → `repository.py:98 replace_book`; test `test_put_replaces_every_writable_field` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `routes.py:95 delete_book` → `repository.py:123 delete_book`; test `test_delete_returns_204_then_the_book_is_gone` |
| R7 | Data stored in SQLite | ✓ implemented | `bookapi/db.py:16 SCHEMA`, `sqlite3.connect`; test `test_data_survives_a_fresh_application_on_the_same_file` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | 201+Location, 200, 204, 404/400/409/413/415 across `routes.py`/`errors.py`; test `test_unknown_route_returns_json_not_html` |
| R9 | Validation: title and author required | ✓ implemented | `validation.py:174-188`; tests `test_invalid_payloads_are_rejected`, `test_all_problems_are_reported_at_once` |
| R10 | GET /health health-check | ✓ implemented | `routes.py:45 health` (queries DB, 503 on failure); test `test_health_reports_ok` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — Setup, Run (flask/gunicorn/python), endpoint contract |
| R12 | At least 3 unit/integration tests | ✓ implemented | 53 tests across 4 files; 0 skipped |

## Build & Test

Scores read from `scores.json` / retort.db — build and tests were **not** re-run (per skill).

```text
test_coverage = 0.99   # tests executed and passed; 99% line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.8333
maintainability = 0.9228
idiomatic     = 0.9
```

```text
pytest -q  (53 tests, 0 skipped)
  tests/test_author_filter.py   7
  tests/test_books_crud.py     19
  tests/test_health.py          7
  tests/test_validation.py     20
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, `bookapi/`) | 649 |
| Lines of code (tests) | 630 |
| Files (excl. .git/__pycache__) | 25 |
| Dependencies (runtime) | 1 (Flask) |
| Tests total | 53 |
| Tests effective | 53 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level enhancements, no deductions:

1. [info] E1 — Consistent JSON error envelope with field-level validation detail
2. [info] E2 — Robustness beyond spec: 409 duplicate ISBN, 413 oversized body, 415 wrong content-type, WAL
3. [info] E3 — Edge cases (out-of-range ids, non-digit year/isbn) return 4xx not 500, with tests

No requirement is missing or partial; no skipped/disabled tests; no build/lint/test failures.

## Architecture

The `run-summary` skill is not available in this environment, so no `summary/` was
generated. Structure is a clean Flask package: `bookapi/__init__.py` (app factory),
`routes.py` (blueprint), `repository.py` (SQL/data access), `db.py` (connection +
schema), `validation.py` (payload cleaning), `errors.py` (typed errors + JSON
handlers); `wsgi.py` entry point; `conftest.py` fixtures; tests split by concern.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=claude-code_effort=max_language=python_model=claude-opus-5_prompt=neutral/rep1
cat scores.json                       # stored mechanical scores (no re-run)
grep -rc "def test_" tests/           # 53 tests
grep -rE "pytest\.skip|xfail" tests/  # 0 skips
# optional independent check:
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt && pytest -q
```
