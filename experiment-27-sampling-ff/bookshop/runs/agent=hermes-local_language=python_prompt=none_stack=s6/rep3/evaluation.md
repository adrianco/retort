# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s6 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, framework=flask, prompt=none, stack=s6
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — from `defect_rate=1.0`, `test_coverage=0.97` in scores.json (not re-run)
- **Lint:** pass — `code_quality=0.789` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

Denominator pinned by `bookshop/REQUIREMENTS.json` (12 requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:60 create_book`; `test_app.py:36 test_create_book` |
| R2 | GET /books lists all | ✓ implemented | `app.py:102 list_books`; `test_app.py:81 test_list_books_with_data` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:108-111`; `test_app.py:93 test_list_books_filter_by_author` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:121 get_book`; `test_app.py:109/120 get_book(+not_found)` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:133 update_book`; `test_app.py:128 test_update_book` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:178 delete_book`; `test_app.py:149 test_delete_book` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:13,29-42` sqlite3 + `books` table |
| R8 | JSON + correct status codes | ✓ implemented | `jsonify` with 201/200/404/400 throughout `app.py` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:79-82`; `test_app.py:54/63 missing_title/author` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:52 health`; `test_app.py:26 test_health` |
| R11 | README with setup/run | ✓ implemented | `README.md` — setup, run, testing, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | 13 tests in `test_app.py`; `test_coverage=0.97 > 0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill Step 2).

```text
scores.json
  test_coverage = 0.97   (build + tests ran; 97% coverage, all passing)
  defect_rate   = 1.0    (build + test succeeded)
  code_quality  = 0.789
  maintainability = 1.0
  idiomatic     = 0.75
  token_efficiency = 0.0182
```

```text
pytest test_app.py  (13 tests, 0 skips)
  grep -cE "^def test_" test_app.py -> 13
  grep skip/xfail    -> 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 362 (app.py 196 + test_app.py 166) |
| Files | 13 (incl. logs/caches; 3 source: app.py, test_app.py, README.md) |
| Dependencies | 1 (flask>=3.0) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Flask app runs with `debug=True` — `app.py:196` (dev-only `__main__` guard)
2. [info] `?author=` filter is exact/case-sensitive — `app.py:109`
3. [info] No pagination on GET /books — `app.py:113`

No requirement-level, build, or test defects. This is a clean, fully-conformant run.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s6/rep3
cat scores.json                                 # mechanical scores (build/test/lint)
grep -cE "^def test_" test_app.py               # 13 tests
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l   # 0 skips
# optional re-run: pip install -r requirements.txt pytest && pytest test_app.py -v
```
