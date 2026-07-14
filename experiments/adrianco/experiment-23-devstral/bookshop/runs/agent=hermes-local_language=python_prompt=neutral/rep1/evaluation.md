# Evaluation: agent=hermes-local_language=python_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=hermes-local (model=devstral), prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective)
- **Build:** pass — from scores (test gate ran)
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** single Flask module + SQLite; see notes below (`run-summary` skill unavailable)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 2 low, 1 info)

Scores from `scores.json`: test_coverage=0.98, code_quality=0.8333, defect_rate=1.0, maintainability=0.9057, idiomatic=0.52, token_efficiency=0.0072.

## Requirements

Pinned checklist from `bookshop/REQUIREMENTS.json` (rest-api-crud, 12 requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `book_api/app.py:29` create_book; test_create_book:23 |
| R2 | GET /books lists all | ✓ implemented | `book_api/app.py:46` list_books; test_list_books:48 |
| R3 | GET /books ?author= filter | ✓ implemented | `book_api/app.py:53` WHERE author=?; test_list_books_with_author_filter:64 |
| R4 | GET /books/{id} single (404) | ✓ implemented | `book_api/app.py:63` get_book; test_get_book:87, test_get_book_not_found:105 |
| R5 | PUT /books/{id} updates | ✓ implemented | `book_api/app.py:74` update_book; test_update_book:109 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `book_api/app.py:93` delete_book; test_delete_book:156 |
| R7 | Data stored in SQLite | ✓ implemented | `book_api/app.py:2,8-23` sqlite3 + CREATE TABLE books |
| R8 | JSON responses, correct codes | ✓ implemented | jsonify + 201/200/404/400/204 throughout app.py |
| R9 | Validation: title & author required | ✓ implemented | `book_api/app.py:33,78` 400 if missing; test_create_book_missing_required_field:37 |
| R10 | GET /health | ✓ implemented | `book_api/app.py:25` health_check; test_health_check:18 |
| R11 | README with setup/run | ✓ implemented | `book_api/README.md` — venv, install, run, endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | 11 tests in `book_api/test_app.py`; test_coverage=0.98 |

## Build & Test

Not re-run (per skill): stored scores are authoritative.

```text
test_coverage = 0.98   → build + tests ran, effectively all passing
defect_rate   = 1.0    → build+test succeeded
code_quality  = 0.8333 → lint/quality gate
```

11 test functions in `book_api/test_app.py`, 0 skips/xfail detected.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 106 (app.py) + 178 (tests) = 284 |
| Files (book_api/) | 5 |
| Dependencies | 2 (flask, pytest) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| API calls / tokens (agent) | 29 calls, 624,374 total tokens (model=devstral) |

## Findings

Top findings (full list in `findings.jsonl`) — none at high/critical:

1. [low] POST/PUT echo client-supplied JSON verbatim instead of the persisted row (`book_api/app.py:44,91`)
2. [low] No test asserts PUT → 404 on a missing id (`book_api/test_app.py:109`)
3. [info] Implementation landed in `book_api/` subdir; root `app.py` is empty because the harness refused the write to the root path (`_agent_stdout.log`)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiment-23-devstral/bookshop/runs/agent=hermes-local_language=python_prompt=neutral/rep1
cat scores.json                                   # stored mechanical scores
grep -cE "def test_" book_api/test_app.py         # 11
grep -rEn "pytest\.skip|xfail" book_api/          # 0
```
