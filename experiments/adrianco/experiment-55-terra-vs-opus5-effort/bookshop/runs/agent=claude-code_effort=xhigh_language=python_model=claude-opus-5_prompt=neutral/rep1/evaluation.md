# Evaluation: claude-code · opus-5 · python · neutral · effort=xhigh · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5, agent=claude-code, prompt=neutral, effort=xhigh
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 57 passed / 0 failed / 0 skipped (57 effective) — parametrized cases expand higher; from `test_coverage=0.99` in `scores.json`, build + all tests passed
- **Build:** pass (`test_coverage=0.99`, `defect_rate=1.0` from `scores.json`) — not re-run
- **Lint:** pass (`code_quality=0.83` from `scores.json`) — not re-run
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 5 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `bookapi/routes.py:91 create_book` → `repository.py:41 create_book` |
| R2 | GET /books lists all books | ✓ implemented | `bookapi/routes.py:99 list_books` → `repository.py:80 list_books` |
| R3 | GET /books ?author= filter | ✓ implemented | `routes.py:101-104` + `repository.py:73 _author_clause` (NOCASE); test `test_list_filters_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `routes.py:113 get_book` + `_load_book` raises NotFoundError; test `test_get_unknown_book_returns_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `routes.py:118 replace_book` → `repository.py:107 update_book`; test `test_put_replaces_every_field` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `routes.py:139 delete_book` → `repository.py:134 delete_book` (204/404) |
| R7 | Data stored in SQLite | ✓ implemented | `bookapi/db.py` sqlite3, schema at `db.py:16`, file-backed via `create_app` DATABASE |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify` throughout routes.py; 201/200/204/400/404/409/503; `errors.py` uniform JSON envelope |
| R9 | Validation: title and author required | ✓ implemented | `validation.py:28 REQUIRED_FIELDS`, `:102` → 400; test `test_create_requires_title_and_author` family |
| R10 | GET /health health check | ✓ implemented | `routes.py:63 health` returns status + DB probe; test `test_health.py` |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` (Requirements/Setup/Run sections, 7.2 KB) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 57 test functions across 4 files; `test_coverage=0.99` (they run) |

## Build & Test

Not re-run per skill guidance — stored scores stand in for the toolchain:

```text
scores.json
test_coverage = 0.99   # build + all tests passed (test gate)
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.833  # lint/quality
maintainability = 0.928
idiomatic     = 0.75
```

Skip scan (`grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail|skipif" tests/`): **0 matches** — no skipped or disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 704 (bookapi/*.py + wsgi.py) |
| Lines of code (tests) | 598 |
| Files (excl. artifacts) | 20 |
| Dependencies (runtime) | 1 (Flask; Werkzeug transitive) |
| Tests total (functions) | 57 |
| Tests effective | 57 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

All findings are informational — no defects, no missing requirements. Top items:

1. [info] Pagination beyond spec on GET /books (`?limit`/`?offset` + `X-Total-Count`)
2. [info] Unique-ISBN conflict handling → 409 (not required)
3. [info] PATCH partial-update route in addition to the required PUT
4. [info] Health check probes the DB and returns 503 on failure
5. [info] `requirements.txt` omits Werkzeug though `errors.py` imports it directly (transitive via Flask)

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=claude-code_effort=xhigh_language=python_model=claude-opus-5_prompt=neutral/rep1"
cat scores.json                       # stored build/test/lint scores (not re-run)
grep -rcE "def test_" tests/*.py      # test counts
grep -rnE "pytest\.skip|xfail|skipif" tests/   # skip scan (empty)
# Optional full re-run:
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && pytest -q
```
