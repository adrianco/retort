# Evaluation: rest-api-crud · effort=medium language=python model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, effort=medium, prompt=neutral (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 46 passed / 0 failed / 0 skipped (46 effective)
- **Build:** pass — scores read from `scores.json` (not re-run)
- **Lint:** pass — code_quality=0.6667 from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

Stored mechanical scores (`scores.json`, not re-run): test_coverage=0.95,
code_quality=0.6667, defect_rate=0.9652, maintainability=0.8956, idiomatic=0.3,
token_efficiency=0.0234. `test_coverage=0.95` ⇒ build succeeded and the full
suite ran and passed (95% line coverage, not a test-gate zero).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `books/app.py:_create` → `books/db.py:create`; 201 + `Location` header |
| R2 | GET /books lists all | ✓ implemented | `books/app.py:_list` → `books/db.py:list_books` (ORDER BY id) |
| R3 | GET /books ?author= filter | ✓ implemented | `books/db.py:52` `WHERE author = ? COLLATE NOCASE`; test_api.py:78 |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `books/app.py:_get:109-113`; test_api.py:62 |
| R5 | PUT /books/{id} updates | ✓ implemented | `books/app.py:_update` → `db.py:update`; test_api.py:98 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `books/app.py:_delete:125-128`; test_api.py:131 |
| R7 | Data stored in SQLite | ✓ implemented | `books/db.py` `sqlite3`; persistence test_api.py:221 |
| R8 | JSON responses, correct status codes | ✓ implemented | `app.py:__call__` JSON body; 201/200/204/400/404/405/409/413/500 |
| R9 | Validation: title & author required | ✓ implemented | `books/validation.py:_required_text`; test_api.py:145 |
| R10 | GET /health | ✓ implemented | `books/app.py:_health:86-93` (200 ok / 503 unavailable) |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` (Setup, Run, env vars, Test sections) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 34 test fns (46 cases w/ parametrize) across tests/; 0 skips |

## Build & Test

Scores read from `scores.json` and the archived `.coverage` (not re-run, per skill §2).

```text
coverage report (from archived .coverage)
books/__init__.py        0   0 100%
books/__main__.py        2   2   0%
books/app.py           147  21  86%
books/db.py             54   0 100%
books/validation.py     60   0 100%
tests/* ...             ... 0 100%
TOTAL                  499  23  95%
```

34 test functions; `@pytest.mark.parametrize` expands isbn-valid (4), isbn-invalid
(5) and year (6), giving 46 effective test cases. No `skip`/`xfail`/`xunit`
markers found.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, books/) | 371 |
| Lines of code (tests) | 402 |
| Files (excl. caches) | 21 |
| Dependencies | 1 (pytest, dev-only) |
| Tests total | 46 cases (34 fns) |
| Tests effective | 46 |
| Skip ratio | 0% |
| Coverage | 95% |

## Findings

All findings are informational (full list in `findings.jsonl`):

1. [info] Server bootstrap (`main`/`__main__`) and the generic 500-error branch
   are uncovered — overall coverage 95%; functional surface fully covered.
2. [info] Low idiomatic score (0.3) — raw `wsgiref`/`sqlite3` rather than a web
   framework; valid and dependency-free, TASK.md names no required framework.

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=medium_language=python_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                              # stored mechanical scores (not re-run)
python3 -I -m coverage report                # from archived .coverage
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l   # 0
# to actually re-run (optional): pip install -r requirements-dev.txt && python -m pytest
```
