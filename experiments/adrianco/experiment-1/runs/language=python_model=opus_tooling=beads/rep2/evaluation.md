# Evaluation: language=python_model=opus_tooling=beads · rep 2

## Summary

- **Factors:** language=python, model=opus, tooling=beads
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — test_coverage=0.97 from retort.db
- **Lint:** pass — code_quality=0.772 from retort.db
- **Architecture:** summary skill not invoked (single-file app, trivial architecture)
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book | ✓ implemented | `app.py:48-62` create_book route, inserts all 4 fields |
| R2 | GET /books lists all books | ✓ implemented | `app.py:64-72` list_books route |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:66-69` filters by author query param |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:74-80` get_book route, 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:82-101` update_book route with validation |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:103-111` delete_book route, returns 204 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:8-21` sqlite3.connect, CREATE TABLE |
| R8 | JSON responses with HTTP status codes | ✓ implemented | All routes use jsonify() with 200/201/204/400/404 |
| R9 | Input validation: title/author required | ✓ implemented | `app.py:52-54` rejects missing fields with 400; `app.py:91-92` validates on update |
| R10 | GET /health endpoint | ✓ implemented | `app.py:44-46` returns {"status":"ok"} |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — pip install, python app.py, endpoints table |
| R12 | At least 3 tests | ✓ implemented | 6 tests in `test_app.py`, test_coverage=0.97 |

## Build & Test

```text
Scores from retort.db (build/test not re-run per skill rules):
  test_coverage=0.97
  code_quality=0.772
  defect_rate=0.613
  maintainability=1.0
  idiomatic=0.7
  token_efficiency=0.5
```

```text
6 test functions in test_app.py:
  test_health
  test_create_and_get_book
  test_create_missing_fields
  test_list_and_filter
  test_update_and_delete
  test_get_missing
0 skipped / 0 xfail
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 191 (117 app + 74 test) |
| Files | 9 |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Build duration | n/a (scores from DB) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [info] No .beads/ directory despite tooling=beads factor
2. [info] code_quality score 0.77 from retort scorer

## Reproduce

```bash
cd experiment-1/runs/language=python_model=opus_tooling=beads/rep2
cat stack.json
cat scores.json 2>/dev/null || sqlite3 -readonly ../../retort.db "SELECT ..."
grep -rE "pytest.skip|@pytest.mark.skip|xfail" . --include="*.py"
grep -cE "^def test_" test_app.py
```
