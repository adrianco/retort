# Evaluation: effort=medium_language=python_model=claude-opus-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-opus-5, prompt=neutral, effort=medium (agent/framework=unknown; Flask + SQLite chosen by the agent)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 15 test functions (one parametrized ×5 ⇒ ~19 cases) passed / 0 failed / 0 skipped (~19 effective)
- **Build:** pass — `test_coverage=0.98`, `defect_rate=1.0` from `scores.json` (build + tests ran)
- **Lint:** pass — `code_quality=0.8333` from `scores.json`
- **Architecture:** run-summary skill unavailable in this session; layout is `app.py` (routes/validation) + `db.py` (SQLite layer) + `test_app.py`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Denominator fixed by `cloud/REQUIREMENTS.json` (task `rest-api-crud`).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:105 create_book` INSERTs all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:119 list_books` returns collection ordered by id |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:121-126` filters by author (COLLATE NOCASE); `test_app.py:72` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:131 get_book`, 404 when absent (`app.py:136`) |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:140 update_book`, partial-update aware; `test_app.py:100,114` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:161 delete_book` returns 204, 404 when absent |
| R7 | Data in SQLite | ✓ implemented | `db.py:7-15` schema, `sqlite3.connect`; `test_app.py:143 test_data_persists` |
| R8 | JSON + appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404/405 handlers `app.py:82-92` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:31-39 _validate`; `test_app.py:42 test_create_requires_title_and_author` |
| R10 | GET /health | ✓ implemented | `app.py:100 health` returns `{"status":"ok"}`; `test_app.py:27` |
| R11 | README with setup + run | ✓ implemented | `README.md` Setup/Run/Tests/API sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 15 test functions in `test_app.py` (well beyond 3) |

No enhancements deducted; three info-level strengths noted in findings.

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json:
  test_coverage = 0.98   (build + tests executed, ~98% line coverage)
  defect_rate   = 1.0    (build + test succeeded)
  code_quality  = 0.8333
  maintainability = 0.8692
  idiomatic     = 0.78
```

```text
Tests (static count from test_app.py):
  15 test functions; test_create_validation_errors is parametrized ×5
  0 skips / 0 xfail
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 217 (app.py 177 + db.py 40) |
| Test LOC | 154 |
| Files | 13 (incl. README, requirements, artifacts) |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 15 fns (~19 cases) |
| Tests effective | ~19 (0 skipped) |
| Skip ratio | 0% |
| Coverage | 0.98 |

## Findings

Top items by severity (full list in `findings.jsonl`) — no issues above info:

1. [info] R3 — author filter is case-insensitive (COLLATE NOCASE), exceeds literal spec
2. [info] R8 — JSON error handlers registered for 404/405/validation
3. [info] R9 — validation rejects bool-as-year and out-of-range years

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-49-versions/cloud/runs/effort=medium_language=python_model=claude-opus-5_prompt=neutral/rep2
cat scores.json
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l
grep -rE "^def test_" test_app.py | wc -l
# optional re-run: python3 -m pytest
```
