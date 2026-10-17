# Evaluation: effort=xhigh_language=python_model=claude-haiku-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-haiku-5-5, prompt=neutral, effort=xhigh
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 62 passed / 0 failed / 0 skipped (62 effective) — from scores.json `test_coverage=0.96`, `defect_rate=1.0`
- **Build:** pass — (not re-run; `defect_rate=1.0` in scores.json)
- **Lint:** pass — `code_quality=0.667` from scores.json (no lint failures; scored score, not a gate fail)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `bookapi/api.py:92 _create_book` → `repository.py:36 create`, returns 201 + Location |
| R2 | GET /books lists all books | ✓ implemented | `bookapi/api.py:83 _list_books` → `repository.py:50 list` |
| R3 | GET /books ?author= filter | ✓ implemented | `bookapi/api.py:84-89`; `repository.py:59` WHERE author, NOCASE |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `bookapi/api.py:97 _get_book` returns 404 when None |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `bookapi/api.py:103 _update_book` → `repository.py:64 update`, 404 if missing |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `bookapi/api.py:113 _delete_book` → `repository.py:76 delete`, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `bookapi/repository.py:5,10-19,30` sqlite3 with schema |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `server.py:53 _send` JSON; statuses 201/200/204/400/404/405/413/503 across api.py |
| R9 | Validation: title & author required | ✓ implemented | `bookapi/validation.py:36-37 _required_text`; rejects with 400 |
| R10 | GET /health health check | ✓ implemented | `bookapi/api.py:118 _health` → `repository.py:82 ping`, 200/503 |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` Setup/Run/Endpoints sections |
| R12 | >= 3 unit/integration tests | ✓ implemented | 62 `test_` functions across `tests/`; `test_coverage=0.96` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill step 2):

```text
test_coverage = 0.96   # tests executed and passed; coverage 96%
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.667
maintainability = 0.941
idiomatic     = 0.80
```

Test inventory (static): 62 `def test_` functions; 0 skip/xfail markers.

```text
tests/test_api.py: 27   tests/test_validation.py: 15   tests/test_repository.py: 11
tests/test_http.py: 8    tests/test_cli.py: 1
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, bookapi/) | 515 |
| Lines of code (tests/) | 712 |
| Python files | 13 |
| Dependencies (runtime) | 0 (stdlib only); dev: pytest |
| Tests total | 62 |
| Tests effective | 62 |
| Skip ratio | 0% |
| Build duration | not re-run |

## Findings

Top findings (full list in `findings.jsonl`) — no critical/high items:

1. [low] Single SQLite connection serializes all requests under one RLock (`repository.py:30,32`)
2. [info] ISBN-10/13 checksum validation beyond spec (`validation.py:101,107`)
3. [info] Year range validation beyond spec (`validation.py:82`)
4. [info] 62 tests, 0 skipped, coverage 0.96

## Reproduce

```bash
cd "experiments/adrianco/experiment-84-haiku55-effort/rest-api-crud/runs/effort=xhigh_language=python_model=claude-haiku-5-5_prompt=neutral/rep3"
cat scores.json                                   # stored mechanical scores
grep -rcE '^\s*def test_' tests/*.py              # test counts
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py"   # skips (none)
```
