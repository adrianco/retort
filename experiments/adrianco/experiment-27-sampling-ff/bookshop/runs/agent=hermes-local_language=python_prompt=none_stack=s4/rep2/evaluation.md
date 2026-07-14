# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s4 · rep 2

## Summary

- **Factors:** language=python, agent=hermes-local (model Qwen3.6-35B-A3B), prompt=none, stack=s4, framework=flask (inferred)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.79` (scores.json)
- **Architecture:** run-summary skill unavailable in this session; app is a single 170-line Flask module (`app.py`) with a SQLite backend — no sub-module structure to summarize
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 2 info)

## Requirements

Checklist from pinned `bookshop/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:54` create_book; `test_app.py:53` test_create_book_success |
| R2 | GET /books lists all books | ✓ implemented | `app.py:89` list_books; `test_app.py:126` test_list_books_with_data |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:91-97` filters by author; `test_app.py:145` test_list_books_filter_by_author |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:106-112`; `test_app.py:177/194` success + not_found |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:116` update_book (partial updates); `test_app.py:207` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:155` delete_book; `test_app.py:287` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:3,15,31` sqlite3 + `books.db` file |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify(...)` with 201/200/404/400 throughout `app.py` |
| R9 | Validation: title and author required | ✓ implemented | `app.py:63-66`; `test_app.py:74/89` missing_title/author → 400 |
| R10 | GET /health health check | ✓ implemented | `app.py:48-50` returns `{"status":"ok"}`; `test_app.py:40` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — install, run, curl examples, testing |
| R12 | >= 3 unit/integration tests | ✓ implemented | 16 tests in `test_app.py`; test_coverage=0.97 |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.97   (coverage fraction; tests executed)
defect_rate   = 1.0    (build + tests succeeded)
code_quality  = 0.79
maintainability = 1.0
idiomatic     = 0.72
token_efficiency = 0.0198
```

Agent self-report (`_agent_stdout.log`): "16/16 passed in 0.07s". No skipped/xfail markers found in `test_app.py`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 169 (app.py) + 311 (test_app.py) = 480 |
| Files (source) | 4 (app.py, test_app.py, requirements.txt, README.md) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build duration | n/a (read from scores) |

## Findings

Top findings (full list in `findings.jsonl`) — no high/critical:

1. [low] F1 — Create response echoes unstripped title/author, can differ from stored/GET value (`app.py:85` vs `app.py:80`)
2. [low] F2 — `init_db()` only runs under `__main__`; table not created under a WSGI server (`app.py:167-169`)
3. [info] F3 — Empty JSON body reports misleading "must be JSON" error (`app.py:56-58`)
4. [info] F4 — Strength: 16 tests cover all endpoints incl. validation/404/filter, 0 skips

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s4/rep2
cat scores.json                 # stored mechanical scores (build/test/lint)
cat ../../../REQUIREMENTS.json  # pinned 12-item checklist
grep -cE "def test_" test_app.py                       # 16
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # 0
# Optional live re-run: pip install -r requirements.txt && pytest test_app.py -v
```
