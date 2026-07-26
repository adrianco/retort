# Evaluation: effort=high_language=python_model=claude-fable-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-fable-5, prompt=neutral, effort=high (agent/framework unknown; Flask + SQLite chosen by the model)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective) — from `test_coverage=0.96`, `defect_rate=1.0` in `scores.json`
- **Build:** pass — not re-run (stored scores used)
- **Lint:** pass — `code_quality=0.7888` from `scores.json`
- **Architecture:** single-module Flask app factory (`create_app`) over SQLite; run-summary skill not available in this environment (skipped)
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Pinned checklist from `cloud/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:91` `create_book` inserts all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:109` `list_books` returns collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:111-116` filters by `author` query param |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:121` `get_book`; 404 at `app.py:125` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:128` `update_book` (partial merge) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:154` `delete_book`, 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:3,25` `sqlite3`, schema `CREATE TABLE books` |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/404/400/204 returned |
| R9 | Validation: title and author required | ✓ implemented | `app.py:57-65` requires non-empty `title`/`author`, 400 otherwise |
| R10 | GET /health | ✓ implemented | `app.py:87` `health` returns `{"status": "ok"}` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Setup/Run/Endpoints/Tests sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test_app.py` — 7 tests, 0 skips; `test_coverage=0.96` |

No prompt-factor requirements: `prompts/neutral.md` prescribes no methodology (covered by R12).

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: test_coverage=0.96  defect_rate=1.0  code_quality=0.7889
             maintainability=1.0  idiomatic=0.82
# test_coverage>0 and defect_rate=1.0 => build succeeded and all tests passed
```

```text
pytest -v   (7 tests: health, create, create-validation, list+author-filter,
             get-single, update, delete)  — 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 280 (app.py 175 + test_app.py 105) |
| Files | 11 (incl. README, requirements.txt, artifacts) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational enhancements, no defects:

1. [info] PUT supports partial updates beyond the spec — `app.py:138`
2. [info] JSON error handlers for 404/405 keep responses consistent — `app.py:163-169`
3. [info] Validation rejects bool-as-year and non-string title/author — `app.py:71`

## Reproduce

```bash
cd runs/effort=high_language=python_model=claude-fable-5_prompt=neutral/rep1
cat scores.json                          # stored build/test/lint scores
grep -cE "^def test_" test_app.py        # 7 tests
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # 0 skips
python3 -m pytest -v                      # optional: re-run tests
```
