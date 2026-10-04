# Evaluation: rest-api-crud-72 · agent=codex effort=low model=gpt-6-astra prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=codex, model=gpt-6-astra, effort=low, prompt=neutral, framework=flask
- **Task type:** REPAIR (a prior failed attempt was present; this run fixed it — see `FEEDBACK.md`)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — test_coverage=0.98 from `scores.json` (tests executed and passed; 0.0 ⇒ did not run)
- **Lint:** pass — code_quality=0.79 from `scores.json`
- **Architecture:** single-module Flask app factory (`create_app`) over stdlib `sqlite3`; see note below (run-summary skill unavailable in this environment)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:94` create_book INSERTs all four fields; `test_app.py:17` test_crud |
| R2 | GET /books lists all books | ✓ implemented | `app.py:105` list_books returns full collection; `test_app.py:24` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:110` WHERE author=?; `test_app.py:36` test_author_filter |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:116` get_book; `app.py:83` find_book raises NotFound; `test_app.py:72` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:120` update_book UPDATE, 404 on no row; `test_app.py:94` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:132` delete_book, 204/404; `test_app.py:30` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:13` sqlite3.connect; `app.py:60` CREATE TABLE books; file persists beside app.py |
| R8 | JSON responses + correct status codes | ✓ implemented | 201 (`app.py:103`), 200, 404, 400 (HTTPException handler `app.py:69`), 204, 503 |
| R9 | Validation: title and author required | ✓ implemented | `app.py:28` non-empty string check → 400; `test_app.py:46` test_invalid_fields |
| R10 | GET /health health check | ✓ implemented | `app.py:89` health returns {"status":"ok"} after DB ping; `test_app.py:83` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md:5` venv+pip+run; tests section; API table |
| R12 | At least 3 tests | ✓ implemented | 10 test methods in `test_app.py`, 0 skipped; test_coverage=0.98 |

No requirement is partial or missing. The repair succeeded: all 12 pinned requirements are met and the full suite runs.

## Build & Test

Build/test not re-run — stored mechanical scores used per skill policy.

```text
scores.json
test_coverage = 0.98   (tests executed and passed; coverage ratio, not a pass gate failure)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.7
token_efficiency = 0.0335  (low — expected for a repair task carrying prior context)
```

Test command (for reference, not executed here): `python -m unittest discover -v`

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 267 (app.py 144 + test_app.py 123) |
| Files (excl. .git, _judge, coverage, agent logs) | 13 |
| Dependencies | 1 (requirements.txt: Flask) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level; no defects:

1. [info] Robust error handling beyond spec (503 on DB errors, JSON 404/405)
2. [info] Strict input validation (unknown-field rejection, year range, trimming)
3. [info] Tests cover persistence across app instances and SQL-injection safety

## Reproduce

```bash
cd experiments/adrianco/experiment-82-codex6-isolated/rest-api-crud-72/runs/agent=codex_effort=low_language=python_model=gpt-6-astra_prompt=neutral/rep1
cat scores.json                       # stored mechanical scores (build/test/lint)
grep -cE "def test_" test_app.py      # 10 tests
grep -rE "skip|xfail" *.py            # 0 skips
python -m unittest discover -v        # optional: re-run suite (not needed; scores stored)
```
