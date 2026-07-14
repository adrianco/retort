# Evaluation: agent=hermes-local language=python prompt=none stack=s4 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (Flask), prompt=none, stack=s4
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 17 tests, 0 skipped (17 effective) — test_coverage=0.97, defect_rate=1.0 (build+tests passed, from scores.json)
- **Build:** pass — from stored scores (not re-run)
- **Lint:** pass — code_quality=0.79, maintainability=0.996, idiomatic=0.72 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:54 create_book` — INSERT with title/author/year/isbn, 201 |
| R2 | GET /books lists all | ✓ implemented | `app.py:98 list_books` — SELECT * FROM books, 200 |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:104-108` — `WHERE author LIKE '%..%'`; test `test_list_books_filter_by_author` |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.py:118 get_book` — 200 / 404 at :124 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:132 update_book` — UPDATE, partial-field default, 200/404 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:174 delete_book` — DELETE, 200/404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:3,15,30` sqlite3 + `books.db`; `init_db()` creates table |
| R8 | JSON responses + correct status codes | ✓ implemented | `jsonify(...)` everywhere; 201/200/400/404 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `app.py:64-67` reject blank title/author with 400; tests cover both |
| R10 | GET /health | ✓ implemented | `app.py:46 health` — `{status: healthy}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — install, run, test, curl examples |
| R12 | At least 3 tests | ✓ implemented | `test_app.py` — 17 tests, 0 skips, test_coverage=0.97 |

## Build & Test

Build/test not re-run — stored mechanical scores used per skill guidance.

```text
scores.json: test_coverage=0.97, defect_rate=1.0, code_quality=0.789,
             maintainability=0.996, idiomatic=0.72, token_efficiency=0.0127
```

```text
Agent stdout: "Test results: 17/17 passed in 0.06s"
grep skip/xfail in test_app.py: 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 194 (app.py) + 311 (test_app.py) = 505 |
| Files | 13 (incl. archive artifacts; 3 deliverable source/doc files) |
| Dependencies | flask, pytest (2) |
| Tests total | 17 |
| Tests effective | 17 |
| Skip ratio | 0% |
| Build duration | n/a (stored score) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Flask runs with `debug=True` and host `0.0.0.0` — `app.py:194` (Werkzeug debugger = RCE risk).
2. [info] `init_db()` executes as an import side effect — `app.py:191`.
3. [info] `?author=` filter uses substring `LIKE` rather than exact match — `app.py:106`.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s4/rep1
cat scores.json                                   # stored mechanical scores
grep -rE "pytest\.skip|xfail" test_app.py | wc -l # skip count (0)
grep -c "def test_" test_app.py                   # 17 tests
# (build/tests already scored; to re-run: pytest test_app.py -v)
```
