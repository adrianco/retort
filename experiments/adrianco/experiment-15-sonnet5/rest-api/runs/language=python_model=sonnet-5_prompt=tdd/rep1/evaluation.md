# Evaluation: language=python_model=sonnet-5_prompt=tdd · rep 1

## Summary

- **Factors:** language=python, model=sonnet-5, prompt=tdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective)
- **Build:** pass — from `test_coverage=1.0` in scores.json (build+import+tests all executed)
- **Lint:** pass — `code_quality=0.8333` from scores.json (no lint re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

Pinned checklist from `../../../REQUIREMENTS.json` (12 requirements, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app/main.py:create_book`, `app/crud.py:create_book`; `tests/test_create_book.py` (201 + fields) |
| R2 | GET /books lists all | ✓ implemented | `app/main.py:list_books`, `app/crud.py:list_books`; `tests/test_list_books.py` |
| R3 | GET /books ?author= filter | ✓ implemented | `app/crud.py:44` `WHERE author = ?`; `test_list_books_filters_by_author` |
| R4 | GET /books/{id} (404 if absent) | ✓ implemented | `app/main.py:get_book` raises 404; `tests/test_get_book.py` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app/main.py:update_book`, `app/crud.py:update_book`; `tests/test_update_book.py` |
| R6 | DELETE /books/{id} | ✓ implemented | `app/main.py:delete_book` 204/404; `tests/test_delete_book.py` |
| R7 | Data stored in SQLite | ✓ implemented | `app/database.py` uses `sqlite3`, `books` table |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/204/404/422 across `app/main.py`; asserted in tests |
| R9 | Validation: title & author required | ✓ implemented | `app/schemas.py` `Field(min_length=1)` → 422; `test_create_book_missing_{title,author}_returns_422` |
| R10 | GET /health | ✓ implemented | `app/main.py:health_check`; `tests/test_health.py` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, test, endpoints, examples) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 14 tests; `test_coverage=1.0` in scores.json |

### Prompt factor: tdd (red/green/refactor discipline)

| ID | Instruction | Status | Evidence |
|----|----|----|----|
| P1 | Write a failing test before implementation | ✓ consistent | One test file per endpoint with focused, behavior-first names; minimal handlers. Agent log states each endpoint's tests were confirmed red first. Red-first *ordering* cannot be reconstructed from static artifacts. |
| P2 | Minimum code to pass | ✓ consistent | Handlers are thin (`app/main.py`), CRUD is direct SQL with no speculative features |
| P3 | Refactor without new behavior | ✓ consistent | Clean 4-layer split (main/schemas/crud/database); no dead code |
| P4 | Tight red/green/refactor cycle | ~ cannot-verify | No per-commit history in the archive; only the final green state (14/14) is observable |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per skill Step 2):

```text
scores.json: test_coverage=1.0  defect_rate=1.0  code_quality=0.8333
             maintainability=0.9715  idiomatic=0.48  token_efficiency=0.00152
```

`test_coverage=1.0` ⇒ the test gate ran the build/import and all tests passed.
Agent log (`_agent_stdout.log`) corroborates: "Verified with pytest (14/14 passing)".

```text
Test inventory (grep):
  tests/test_create_book.py   3
  tests/test_list_books.py    3
  tests/test_update_book.py   3
  tests/test_get_book.py      2
  tests/test_delete_book.py   2
  tests/test_health.py        1
  total: 14   skipped/xfail: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, app/) | 124 |
| Lines of code (tests) | 108 |
| Files (source, .py) | 12 |
| Dependencies (requirements.txt) | 5 |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Build | pass (test_coverage=1.0) |

## Findings

Full list in `findings.jsonl`. No findings at medium severity or above.

1. [low] New SQLite connection opened/closed on every CRUD call (`app/crud.py`) — fine at this scale.
2. [info] `?author=` filter is exact-match only (`app/crud.py:44`) — satisfies spec.
3. [info] No ISBN format validation (`app/schemas.py:9`) — beyond spec.
4. [info] Idiomatic score 0.48 from scorer — informational; no concrete defect.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=python_model=sonnet-5_prompt=tdd/rep1
cat scores.json                                   # mechanical scores (do not re-run toolchain)
grep -rE "^\s*def test_" tests/ | wc -l           # 14 tests
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" tests/   # 0 skips
python3 -m pytest                                 # optional: 14/14 pass
```
