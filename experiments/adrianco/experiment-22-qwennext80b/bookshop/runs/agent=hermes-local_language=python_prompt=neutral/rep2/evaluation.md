# Evaluation: agent=hermes-local language=python prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (model=Qwen3-Coder-Next), framework=Flask, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective) — `test_coverage=0.92`, `defect_rate=1.0` from `scores.json`
- **Build:** pass (import + test gate succeeded; `defect_rate=1.0`) — not re-run
- **Lint:** pass — `code_quality=0.79` from `scores.json`
- **Architecture:** run-summary skill not invoked (not registered as invocable this session); single-module Flask app, see notes below
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:95 create_book`, INSERT at :109; `test_create_book` (test_api.py:47) |
| R2 | GET /books lists all books | ✓ implemented | `app.py:135 list_books`; `test_list_books` (test_api.py:110) |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:142-143` LIKE filter; `test_list_books_with_author_filter` (test_api.py:134) |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:158 get_book`, 404 at :167; `test_get_book_not_found` (test_api.py:180) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:179 update_book`; `test_update_book` (test_api.py:188) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:241 delete_book`; `test_delete_book` (test_api.py:260) |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:18,33` sqlite3 connect; schema at :35-44 |
| R8 | JSON responses with correct HTTP codes | ✓ implemented | `jsonify` + 201/200/404/400/500 throughout `app.py` |
| R9 | Validation: title and author required | ✓ implemented | `app.py:49-67 validate_book`; `test_create_book_validation` (test_api.py:69) |
| R10 | GET /health health check | ✓ implemented | `app.py:84 health_check`; `test_health_check` (test_api.py:38) |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` install/usage/testing sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 13 tests in `test_api.py`; `test_coverage=0.92` |

## Build & Test

Not re-run — stored mechanical scores used per skill guidance.

```text
scores.json: test_coverage=0.92, defect_rate=1.0, code_quality=0.7889,
             maintainability=0.9703, idiomatic=0.68, token_efficiency=0.0128
```

`defect_rate=1.0` ⇒ the import/build + full test suite executed and passed.
`test_coverage=0.92` is a coverage ratio (statement coverage), not a pass-rate — all 13 tests pass.

```text
grep -cE "^def test_" test_api.py  => 13
grep skip/xfail                    => 0   (no skipped or disabled tests)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 260 |
| Lines of code (test_api.py) | 292 |
| README lines | 125 |
| Files (source: app.py, test_api.py, README.md) | 3 |
| Dependencies | 1 (flask; unpinned) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Test coverage | 92% |
| Agent tokens (total / api calls) | 647,583 / 24 |

## Findings

Full list in `findings.jsonl`. No critical/high/medium findings.

1. [low] F1 — PUT does not type/range-validate year and isbn (create does) — `app.py:213-219`
2. [low] F2 — Author filter uses unescaped LIKE substring match (`%`/`_` act as wildcards) — `app.py:143`
3. [low] F3 — No pinned dependency file; README says `pip install flask` unversioned — `README.md:22`
4. [info] F4 — Partial updates supported beyond spec (positive enhancement) — `app.py:195-225`

## Reproduce

```bash
cd experiment-22-qwennext80b/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep2
cat scores.json                                   # stored mechanical scores
grep -cE "^def test_" test_api.py                 # 13 tests
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0 skips
# To re-run tests yourself (optional; not required for scoring):
# python -m pytest test_api.py -v
```
