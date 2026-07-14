# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s4 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (Flask), prompt=none, stack=s4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — from `defect_rate=1.0` in scores.json (build + tests succeeded)
- **Lint:** pass — `code_quality=0.79` in scores.json (no blocking lint failures)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

All requirements from the pinned `REQUIREMENTS.json` (12-item checklist) are met, and
the full test suite passes. `test_coverage=0.97` and `defect_rate=1.0` confirm the
build and all tests ran and passed. The `_agent_stdout.log` file-mutation warning is a
transient artifact from an intermediate write attempt against a read-only path; the
final writes landed (all four deliverables exist and are correct).

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:49 create_book` inserts title/author/year/isbn, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:84 list_books` returns full collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:90-94` LIKE filter; `test_list_books_with_filter` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:102 get_book`, 404 when absent |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:114 update_book`, partial-update semantics |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:148 delete_book`, 404 when absent |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:27 init_db`, `sqlite3`, `books.db` present |
| R8 | JSON responses + status codes | ✓ implemented | `jsonify` + explicit 201/200/404/400 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:59-62`; `test_create_book_missing_title/_author` |
| R10 | GET /health | ✓ implemented | `app.py:43 health_check` returns `{"status":"healthy"}` |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` — setup, run, usage, testing sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 12 tests in `test_app.py`, all pass |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.97   # tests executed; 97% line coverage
defect_rate   = 1.0    # build + all tests passed
code_quality  = 0.7888
maintainability = 1.0
idiomatic     = 0.76
```

```text
pytest test_app.py  (from _agent_stdout.log)
12/12 passed — 0 failed, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 366 (app.py 167 + test_app.py 199) |
| Files (workspace, top level) | 14 (4 deliverables + artifacts) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (scores cached) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] `init_db()` runs as an import side effect — `app.py:164`
2. [info] `?author=` uses substring LIKE match, not exact — `app.py:92`
3. [info] code_quality 0.79 / idiomatic 0.76 — moderate quality, no defects

No critical, high, or medium findings. This is a clean pass.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s4/rep3
cat scores.json                                   # cached build/test/lint scores
grep -rEc "^def test_" test_app.py                # test count = 12
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # skips = 0
# optional re-run: pip install -r requirements.txt && pytest test_app.py -v
```
