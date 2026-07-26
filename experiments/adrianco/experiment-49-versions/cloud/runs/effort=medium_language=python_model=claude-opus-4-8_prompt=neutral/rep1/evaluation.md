# Evaluation: effort=medium_language=python_model=claude-opus-4-8_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-4-8, prompt=neutral, effort=medium
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass (import/collection succeeded) — from `scores.json`
- **Lint:** pass — code_quality=0.79 (from `scores.json`)
- **Architecture:** single-module Flask app factory (`create_app`) + SQLite; see notes below (`run-summary` skill unavailable in this session)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

Stored scores (`scores.json`): test_coverage=0.96, defect_rate=1.0, maintainability=1.0,
code_quality=0.79, idiomatic=0.77, token_efficiency=0.018. defect_rate=1.0 and
test_coverage>0 confirm the build succeeded and all tests ran and passed.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:89` `create_book`, INSERT with all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:112` `list_books`, SELECT * ORDER BY id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:115-119` filters `WHERE author = ?`; tested `test_app.py:71` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:124` `get_book`, 404 at `:131`; tested `test_app.py:57` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:134` `update_book`, partial merge; tested `test_app.py:78` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:169` `delete_book`, 204/404; tested `test_app.py:97` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:5,19` `sqlite3.connect`, CREATE TABLE books |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/404/400/204 used |
| R9 | Validation: title and author required | ✓ implemented | `app.py:50-67` `validate_payload`; tested `test_app.py:35` |
| R10 | GET /health health check | ✓ implemented | `app.py:85` returns `{"status":"ok"}`, 200; tested `test_app.py:15` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — venv/install/run/test/API sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 10 tests in `test_app.py`, test_coverage=0.96 |

No enhancements beyond spec change the score; PUT supports partial updates and rejects empty
payloads (400), both reasonable additions.

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: test_coverage=0.96  defect_rate=1.0  maintainability=1.0
=> build/import succeeded, 10/10 tests passed, 0 skipped (grep: 0 skip markers)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 290 (app.py 182 + test_app.py 108) |
| Files | 9 (excl. __pycache__, .coverage, agent logs) |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] SQLite `books.db` persists across restarts with no documented reset
2. [info] 10 tests provided, well beyond the 3 required
3. [info] PUT rejects an empty update payload with 400

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=medium_language=python_model=claude-opus-4-8_prompt=neutral/rep1
cat scores.json
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l
grep -c "def test_" test_app.py
# optional full re-run:
python3 -m pytest
```
