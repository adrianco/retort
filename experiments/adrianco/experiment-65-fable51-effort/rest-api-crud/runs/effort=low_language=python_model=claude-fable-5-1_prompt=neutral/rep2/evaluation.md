# Evaluation: effort=low_language=python_model=claude-fable-5-1_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-fable-5-1, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — test_coverage=0.95 (retort.db/scores.json)
- **Build:** pass — import/collection succeeded (test_coverage=0.95 > 0)
- **Lint:** pass — code_quality=0.79 (scores.json); no re-run
- **Architecture:** single-module stdlib service (`app.py`); summary skill not invoked (small single-file run)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:229 _create_book` → `BookStore.create` (app.py:67); test `test_create_and_get_book` |
| R2 | GET /books lists all | ✓ implemented | `app.py:224 _list_books` → `store.list`; test `test_list_and_filter_by_author` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:225-227` parses `author`; `BookStore.list` WHERE author (app.py:79-82) |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:242 _get_book`, 404 when absent (app.py:244-245) |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:248 _update_book` → `store.update`; test `test_update_book` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:257 _delete_book` → `store.delete`; test `test_delete_book` |
| R7 | SQLite persistence | ✓ implemented | `sqlite3.connect` (app.py:39), schema at app.py:43-56 |
| R8 | JSON + correct status codes | ✓ implemented | `_send_json` (app.py:160); 201/200/404/400/405/204 throughout |
| R9 | Validate title/author required | ✓ implemented | `validate_book` (app.py:117-120); test `test_create_validation_errors` |
| R10 | GET /health | ✓ implemented | `app.py:188-189` returns `{"status":"ok"}`; test `test_health` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, endpoints) |
| R12 | ≥3 tests | ✓ implemented | 9 test functions in `tests/test_api.py`; test_coverage=0.95 |

## Build & Test

Not re-run — stored mechanical scores used per skill guidance.

```text
scores.json: test_coverage=0.95  defect_rate=1.0  code_quality=0.7889
             maintainability=0.9388  idiomatic=0.78  token_efficiency=0.0194
```

test_coverage=0.95 and defect_rate=1.0 ⇒ the module imported, tests collected, and all tests passed.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 292 (app.py) + 135 (tests) = 427 |
| Files | 12 (incl. artifacts) |
| Dependencies | 1 (pytest, test-only; runtime is stdlib-only) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] ISBN format validation beyond spec — `app.py:140-144`
2. [info] Location header + 201/204 REST semantics — `app.py:234-260`

No requirement, build, test, or skip findings. Clean run.

## Reproduce

```bash
cd runs/effort=low_language=python_model=claude-fable-5-1_prompt=neutral/rep2
cat scores.json                                # stored mechanical scores
python -m pytest tests/ -q                     # 9 tests (optional re-run; not done here)
grep -cE "^def test_" tests/test_api.py        # 9
```
