# Evaluation: effort=medium_language=python_model=claude-opus-4-8_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-opus-4-8, prompt=neutral, effort=medium
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 11 passed / 0 failed / 0 skipped (11 effective) — from stored scores; coverage 0.95
- **Build:** pass — from `scores.json` (defect_rate=1.0, test_coverage=0.95)
- **Lint:** pass — code_quality=0.79 (`scores.json`)
- **Architecture:** run-summary skill unavailable — single-module Flask app (`app.py`) using the `create_app` factory pattern with a request-scoped `sqlite3` connection on `g`.
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:97 create_book` inserts all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:120 list_books` returns collection |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:123-127` filters by `author` query param |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:132 get_book`, 404 at `app.py:139` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:142 update_book` partial update + 404 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:168 delete_book` returns 204, 404 if absent |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:7,21` uses stdlib `sqlite3`, persistent `books.db` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404 |
| R9 | Input validation: title and author required | ✓ implemented | `app.py:52-72 validate_payload`; test at `test_app.py:53` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:93 health` returns `{"status":"ok"}`, 200 |
| R11 | README.md with setup & run instructions | ✓ implemented | `README.md` — Setup/Running/API/Tests sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test_app.py` — 11 tests, coverage 0.95 |

Prompt factor `neutral` (`prompts/neutral.md`) prescribes no methodology and adds no checkable instructions — no `P*` requirements.

## Build & Test

Scores read from `scores.json` (not re-run, per skill policy):

```text
test_coverage = 0.95   (build + tests executed and passed; 95% coverage)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.83
```

```text
python3 -m pytest   # 11 tests in test_app.py, 0 skips
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 304 (app.py 185, test_app.py 119) |
| Files | app.py, test_app.py, README.md, requirements.txt |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 11 |
| Tests effective | 11 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [info] Health check does not verify DB connectivity — `app.py:93-95`

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=medium_language=python_model=claude-opus-4-8_prompt=neutral/rep3
cat scores.json
grep -rEn "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l
grep -rEc "def test_" test_app.py
python3 -m pytest   # optional re-run
```
