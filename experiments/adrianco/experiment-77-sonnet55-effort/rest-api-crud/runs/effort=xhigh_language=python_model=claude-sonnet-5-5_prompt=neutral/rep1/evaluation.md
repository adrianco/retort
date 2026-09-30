# Evaluation: effort=xhigh_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=xhigh
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 60 passed / 0 failed / 0 skipped (60 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.83` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores read from `scores.json` (inline gate output; no rebuild): `test_coverage=0.97`, `defect_rate=1.0`, `code_quality=0.833`, `maintainability=0.881`, `idiomatic=0.88`. The `neutral` prompt prescribes no methodology and adds no checkable instructions, so there are no `P*` requirements — TASK.md / `REQUIREMENTS.json` is the whole spec.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:_create_book`; `db.py:create`; `test_api.py:test_create_returns_201_with_location_and_full_book` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:_list_books`; `test_api.py:test_lists_all_books_in_id_order` |
| R3 | GET /books ?author= filter | ✓ implemented | `db.py:list_books` WHERE casefold(author); `test_api.py:test_author_filter` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:_get_book`; `test_api.py:test_get_existing_book`, `test_missing_or_malformed_id_returns_404` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:_update_book`; `test_api.py:test_full_update`, `test_partial_update_keeps_other_fields` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:_delete_book`; `test_api.py:test_delete_returns_204_and_removes_book` |
| R7 | Data stored in SQLite | ✓ implemented | `db.py:BookRepository` uses `sqlite3`; schema at `db.py:_SCHEMA`; `test_repository.py` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `app.py:_send` sets `application/json`; 201/200/204/400/404/405/413/500 across `test_api.py` |
| R9 | Validation: title & author required | ✓ implemented | `validation.py:validate_book` REQUIRED_FIELDS; `test_api.py:test_invalid_payload_returns_400_naming_each_bad_field`; `test_validation.py` |
| R10 | GET /health health check | ✓ implemented | `app.py:_health`; `test_api.py:test_health_ok`, `test_health_reports_unavailable_when_db_is_closed` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` Setup/Run sections (`python -m bookapi`, `pytest`) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 60 test functions across 4 files; `test_coverage=0.97` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate during `retort run`):

```text
defect_rate    = 1.0    -> build + tests succeeded
test_coverage  = 0.97   -> coverage / pass signal (tests executed)
code_quality   = 0.833  -> lint/quality
maintainability= 0.881
idiomatic      = 0.88
```

Skip scan (`grep pytest.skip|@pytest.mark.skip|xfail tests/`): 0 skips. Effective tests = 60.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 462 (src) |
| Lines of code (tests) | 663 |
| Files (src + tests) | 10 |
| Dependencies (runtime) | 0 (`pytest` test-only) |
| Tests total | 60 |
| Tests effective | 60 |
| Skip ratio | 0% |
| Build duration | not re-run (scores from gate) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level enhancements beyond spec, no deductions:

1. [info] Zero runtime dependencies — hand-rolled WSGI router over stdlib only
2. [info] Error handling beyond spec: 405+Allow, 413 oversized body, JSON 500 without leaking details
3. [info] Unicode-aware, case-insensitive exact author filter via custom SQLite `casefold()`

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=xhigh_language=python_model=claude-sonnet-5-5_prompt=neutral/rep1
cat scores.json                                                   # mechanical scores (no rebuild)
grep -rEc "def test_" tests/*.py                                  # 60 test functions
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py" | wc -l   # 0 skips
# optional independent re-run: PYTHONPATH=src pytest -q
```
