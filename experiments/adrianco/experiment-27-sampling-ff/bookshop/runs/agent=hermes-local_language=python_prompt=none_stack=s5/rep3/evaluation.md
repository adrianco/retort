# Evaluation: agent=hermes-local_language=python_prompt=none_stack=s5 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, prompt=none, stack=s5, framework=unknown (Flask)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 18 passed / 0 failed / 0 skipped (18 effective)
- **Build:** pass — from `test_coverage=0.92`, `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.79` (scores.json)
- **Architecture:** summary skill unavailable in this session — see app.py (single-module Flask app + SQLite)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 2 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:90 create_book` — inserts all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:135 list_books` — returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:141-147` — `WHERE author LIKE ?`; `test_app.py:151 test_list_books_filter_by_author` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:157 get_book` — 404 on miss (`app.py:167`) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:172 update_book` — partial update supported |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:222 delete_book` — 404 on miss, 200 on delete |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:3,36` sqlite3; `books.db` file present in workspace |
| R8 | JSON responses + correct status codes | ✓ implemented | `jsonify(...)` with 201/200/404/400 throughout `app.py` |
| R9 | Input validation: title & author required | ✓ implemented | `app.py:101-105` — 400 when missing; `test_app.py:68,80` |
| R10 | GET /health health check | ✓ implemented | `app.py:84 health_check` — returns `{status: healthy}` 200 |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — setup, run, testing, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 18 tests across 7 classes; test_coverage=0.92 |

## Build & Test

Scores read from `scores.json` (not re-run per skill guidance):

```text
test_coverage = 0.92   # build + tests executed and passed; 92% line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.789
maintainability = 0.972
idiomatic     = 0.70
token_efficiency = 0.0097
```

Agent self-report (`_agent_stdout.log`): "18 passed in 0.07s".

## Metrics

| Metric | Value |
|--------|-------|
| Lines (app.py) | 242 |
| Lines (test_app.py) | 367 |
| Source files (app, test, requirements, README) | 4 |
| Dependencies | 2 (flask, pytest) |
| Tests total | 18 |
| Tests effective | 18 |
| Skip ratio | 0% |
| Line coverage | 92% |

## Findings

Top items (full list in `findings.jsonl`):

1. [low] ~8% of lines uncovered — file-backed DB branch and `__main__` runner never exercised (tests use `:memory:`)
2. [low] Author filter concatenates the query param into the LIKE pattern (still parameterized — no injection; LIKE wildcards treated as wildcards)
3. [info] R3 author filter is substring matching (`LIKE %..%`) rather than exact — acceptable interpretation

No critical or high-severity findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s5/rep3
pip install -r requirements.txt
pytest test_app.py -v        # 18 passed
```
