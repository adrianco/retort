# Evaluation: effort=default·language=python·model=claude-fable-5·prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-fable-5, prompt=neutral, effort=default (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — from stored scores
- **Build:** pass — test_coverage=0.96, defect_rate=1.0 (from scores.json; toolchain not re-run)
- **Lint:** pass — code_quality=0.79 (from scores.json)
- **Architecture:** single Flask app factory (`create_app`) over SQLite; summary skill unavailable, so no `summary/index.md` generated
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Pinned checklist from `REQUIREMENTS.json` (rest-api-crud, 12 requirements).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:102` create_book; test `test_app.py:33` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:125` list_books; test `test_app.py:75` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:129-132` WHERE author=?; test `test_app.py:84` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:137` get_book, 404 at :143; test `test_app.py:93` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:146` update_book; test `test_app.py:104` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:171` delete_book, 404 on rowcount==0; test `test_app.py:129` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:3,9-17,24` sqlite3 + schema |
| R8 | JSON responses + status codes | ✓ implemented | `app.py:123,135,143,178` jsonify with 201/200/404/204; handlers :86-96 |
| R9 | Validation: title/author required | ✓ implemented | `app.py:48-64` validate_payload; test `test_app.py:52` |
| R10 | GET /health | ✓ implemented | `app.py:98` health; test `test_app.py:27` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, API, examples, tests) |
| R12 | ≥3 unit/integration tests | ✓ implemented | 9 tests in `test_app.py`; test_coverage=0.96 |

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: test_coverage=0.96, defect_rate=1.0, maintainability=1.0,
             code_quality=0.789, idiomatic=0.67
# defect_rate=1.0 ⇒ build + tests passed; 0 skips (grep of test_app.py)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source: app.py) | 184 |
| Lines of code (tests) | 142 |
| Files (excl. caches) | 12 |
| Dependencies | 2 (flask, pytest) |
| Tests total | 9 |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top items (full list in `findings.jsonl`) — all info-level, no defects:

1. [info] PUT partial-update support beyond spec (enhancement)
2. [info] Dedicated JSON 400/404/405 error handlers (enhancement)
3. [info] Line coverage 96%, not 100% (`__main__` guard uncovered)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=default_language=python_model=claude-fable-5_prompt=neutral/rep1
cat scores.json
grep -cE "^def test_" test_app.py
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l
# optional independent verification:
pip install -r requirements.txt && pytest
```
