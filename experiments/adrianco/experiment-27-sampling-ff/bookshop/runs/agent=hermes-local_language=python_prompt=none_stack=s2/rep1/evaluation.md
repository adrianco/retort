# Evaluation: agent=hermes-local language=python prompt=none stack=s2 · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local (Qwen3.6-35B-A3B), prompt=none, stack=s2, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective) — from stored scores; not re-run
- **Build:** pass — test_coverage=0.95, defect_rate=1.0 (from `scores.json`)
- **Lint:** pass — code_quality=0.79 (from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 3 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:61-100` create_book; test_app.py:43 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:105-118` list_books; test_app.py:80 |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:109-114` LIKE filter; test_app.py:88 |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:123-132`; test_app.py:106,116 |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:137-178`; test_app.py:125,140 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:183-195`; test_app.py:149,161 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,28-41` sqlite3; `books.db` present |
| R8 | JSON responses + appropriate status codes | ✓ implemented | jsonify with 201/200/404/400/415 throughout `app.py` |
| R9 | Validation: title and author required | ✓ implemented | `app.py:72-76,153-157`; test_app.py:57,64 |
| R10 | GET /health health check | ✓ implemented | `app.py:53-56`; test_app.py:32 |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` setup/run/test/curl examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 13 tests in `test_app.py`; test_coverage=0.95 |

## Build & Test

Not re-run — stored mechanical scores from `scores.json` (per evaluate-run policy):

```text
test_coverage = 0.95   # build + tests ran; near-full coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.79
maintainability = 1.0
idiomatic     = 0.70
```

Agent self-report (`_agent_stdout.log`): "All 13 tests pass (13/13)."
Skip scan: 0 skipped/xfail tests found.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 366 (app.py 202, test_app.py 164) |
| Files (excl. db/coverage/pycache) | 12 |
| Dependencies | 2 (flask>=2.0, pytest>=7.0) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Token usage | 295,992 total (25,892 in / 10,004 out); token_efficiency=0.017 |

## Findings

Full list in `findings.jsonl` (all low severity — no requirement gaps):

1. [low] Duplicate ISBN raises unhandled 500 — `app.py:36,90,170` (isbn UNIQUE, IntegrityError uncaught)
2. [low] Unreachable 400 branch in create_book — `app.py:66-67` (get_json raises 415 first)
3. [low] debug=True bound to 0.0.0.0 — `app.py:202`

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s2/rep1
cat scores.json                       # stored mechanical scores (no re-run)
grep -rEn "pytest\.skip|xfail" . --include="*.py" | wc -l   # skip scan → 0
# optional re-run: pip install -r requirements.txt && pytest test_app.py -v
```
