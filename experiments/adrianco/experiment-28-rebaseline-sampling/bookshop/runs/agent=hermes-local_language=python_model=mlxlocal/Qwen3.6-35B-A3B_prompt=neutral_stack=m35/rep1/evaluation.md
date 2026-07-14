# Evaluation: agent=hermes-local language=python model=mlxlocal/Qwen3.6-35B-A3B prompt=neutral stack=m35 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35, framework=Flask (from code)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective)
- **Build:** pass (test_coverage=0.98, defect_rate=1.0 from scores.json — no re-run)
- **Lint:** pass — code_quality=0.79 (from scores.json); 1 low lint note
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

Pinned checklist from `REQUIREMENTS.json` (constant denominator = 12). Prompt factor `neutral` adds no checkable instructions (it only states no methodology is prescribed), so there are no `P*` requirements.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:49 create_book` inserts all 4 fields; `test_app.py:51 test_create_book_success` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:86 list_books`; `test_app.py:121 test_list_books_with_data` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:92-95` `WHERE author = ?`; `test_app.py:136 test_list_books_filter_by_author` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:112 get_book` (404 at :119); `test_app.py:156/168` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:130 update_book`; `test_app.py:178 test_update_book_success` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:170 delete_book`; `test_app.py:204 test_delete_book_success` (verifies 404 after) |
| R7 | Data stored in SQLite/embedded DB | ✓ implemented | `app.py:29 init_db` CREATE TABLE, sqlite3 to `books.db` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `jsonify(...)` with 201/200/404/400 throughout `app.py` |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:62-66` rejects missing/blank/non-str; `test_app.py:68/79/90` |
| R10 | GET /health health-check endpoint | ✓ implemented | `app.py:43 health` returns `{status: healthy} 200`; `test_app.py:38/42` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — setup, run, test, curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 16 tests in `test_app.py` (`grep def test_` = 16); test_coverage=0.98 |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
scores.json: test_coverage=0.98  defect_rate=1.0  code_quality=0.789
             maintainability=0.995  idiomatic=0.72  token_efficiency=0.021
```

`test_coverage=0.98` and `defect_rate=1.0` ⇒ build imported cleanly and all
tests passed. Agent stdout reports "Test results: 16/16 passed". No skipped,
xfail, or disabled tests found (`grep pytest.skip|xfail` = 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 411 (app.py 189, test_app.py 222) |
| Files | 14 (incl. archive metadata + books.db) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [low] Dead indirection: `_test_db_path` attribute is never set — `app.py:13` getattr always falls back to module global.
2. [info] `?author=` filter is exact-match only (`app.py:94`) — satisfies R3; fuzzy match not supported (not required).

No critical/high/medium findings. This run is spec-complete and passes all tests.

## Reproduce

```bash
cd experiment-28-rebaseline-sampling/bookshop/runs/agent=hermes-local_language=python_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35/rep1
cat scores.json                                   # mechanical scores (no re-run)
grep -rE "def test_" test_app.py | wc -l          # 16 tests
grep -rE "pytest\.skip|xfail" . --include="*.py" | wc -l   # 0 skips
python -m pytest test_app.py -v                   # optional: 16 passed
```
