# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s8 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, framework=Flask (inferred), prompt=none, stack=s8
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 20 passed / 0 failed / 0 skipped (20 effective)
- **Build:** pass — from `defect_rate=1.0` in scores.json (build + tests succeeded)
- **Lint:** pass — code_quality=0.79 (no blocking warnings)
- **Architecture:** see `summary/index.md`
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 4 info)

Scores (from `scores.json`): test_coverage=0.96, defect_rate=1.0, code_quality=0.789,
maintainability=0.998, idiomatic=0.67, token_efficiency=0.019.

A clean, complete run. Every pinned requirement is implemented and exercised by a
passing test; there are no missing or partial requirements and no skipped tests.

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:61` create_book; `test_app.py:45` test_create_book |
| R2 | GET /books lists all books | ✓ implemented | `app.py:106` list_books; `test_app.py:84` test_list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:112-116` LIKE filter; `test_app.py:104` test_list_books_by_author |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:123` get_book, 404 at `app.py:130`; `test_app.py:124,139` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:135` update_book; `test_app.py:145` test_update_book |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:182` delete_book; `test_app.py:163` test_delete_book |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:15,28-41` sqlite3 + books.db schema |
| R8 | JSON responses + appropriate status codes | ✓ implemented | jsonify throughout; 201/200/400/404/409 |
| R9 | Validation: title and author required | ✓ implemented | `app.py:75-79`; `test_app.py:62,73` missing-title/author → 400 |
| R10 | GET /health health check | ✓ implemented | `app.py:55` health_check; `test_app.py:37` test_health_check |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — install, run, usage, testing sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 20 tests in `test_app.py`; test_coverage=0.96 > 0 |

Enhancements beyond spec (not deductions): year type/range validation, 409 on
duplicate ISBN, partial PUT updates, substring author matching. See findings.

## Build & Test

Not re-run — stored scores from `scores.json` used as the build+test signal:

```text
defect_rate = 1.0     → build + tests succeeded
test_coverage = 0.96  → tests executed; ~96% line coverage
```

Agent's own report (`_agent_stdout.log`): "Test results: 20/20 passed in 0.06s".
Skip scan (`grep pytest.skip|@pytest.mark.skip|xfail test_app.py`): 0 matches.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | ~200 (app.py) + ~290 (test_app.py) |
| Files (non-artifact) | app.py, test_app.py, requirements.txt, README.md |
| Dependencies | 2 (flask, pytest) |
| Tests total | 20 |
| Tests effective | 20 |
| Skip ratio | 0% |
| Build/test | pass (defect_rate=1.0) |

## Findings

Top items by severity (full list in `findings.jsonl` — no critical/high/medium):

1. [low] Moderate idiomatic/quality scores (idiomatic=0.67, code_quality=0.79); validation block duplicated between create_book and update_book (`app.py:75-88` vs `154-167`).
2. [info] Year validation beyond spec — type + range 0..2100 (`app.py:82-88`).
3. [info] Duplicate-ISBN handling returns 409 (`app.py:102-103`, `178-179`).
4. [info] PUT supports partial updates (`app.py:148-151`).
5. [info] Author filter uses substring LIKE match (`app.py:113-116`).

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s8/rep1
cat scores.json                                  # build/test signal (defect_rate, test_coverage)
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l   # skip scan → 0
grep -cE "^def test_" test_app.py                # test count → 20
# optional re-run: pip install -r requirements.txt && pytest test_app.py -v
```
