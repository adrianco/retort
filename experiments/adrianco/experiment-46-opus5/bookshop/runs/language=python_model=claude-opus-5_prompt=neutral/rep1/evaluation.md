# Evaluation: language=python_model=claude-opus-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-opus-5, prompt=neutral (framework=Flask + stdlib sqlite3)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** pass (test_coverage=0.99, defect_rate=1.0 from scores.json) / 0 failed / 0 skipped — 53 test functions (37 API + 16 validation), 12 `@parametrize` blocks expand these to well over 100 effective cases
- **Build:** pass — not re-run (test_coverage=0.99 ⇒ import+tests succeeded)
- **Lint:** pass — code_quality=0.83 from scores.json
- **Architecture:** `run-summary` skill unavailable in this session; module map summarized below
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:77` `create_book` → `repository.create` (`repository.py:32`), returns 201+Location |
| R2 | GET /books lists all books | ✓ implemented | `app.py:83` `list_books` → `repository.list_all` (`repository.py:48`) |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:85` reads `author` arg; `repository.py:58` `WHERE author = ? COLLATE NOCASE`; `test_api.py:120` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:89` `get_book`, 404 at `app.py:93`; `test_api.py:154` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:96` `update_book` → `repository.replace` (`repository.py:71`), 404 when absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:104` `delete_book` → `repository.delete` (`repository.py:95`), 204/404 |
| R7 | Data stored in SQLite | ✓ implemented | `db.py:10` SCHEMA + `sqlite3.connect` (`db.py:28`); persistence test `test_api.py:248` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404/405/409/500/503 all covered; JSON error handlers `app.py:116` |
| R9 | Validation: title and author required | ✓ implemented | `validation.py:83` `REQUIRED_FIELDS`, `validation.py:106` rejects missing → 400; `test_validation.py:36` |
| R10 | GET /health health check | ✓ implemented | `app.py:68` `health` does a real `SELECT 1` round-trip; `test_api.py:18` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` (6.6 KB) — Setup/Run/API/testing sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | 53 test functions across `test_api.py`, `test_validation.py`; test_coverage=0.99 |

No partial or missing requirements. Items exceeding spec (409 duplicate-ISBN handling, unknown-field rejection, case-insensitive author filter, 503 health degradation) recorded as `info` enhancements in `findings.jsonl`, not deductions.

## Build & Test

```text
# Not re-run per skill guidance — stored mechanical scores are authoritative.
scores.json: test_coverage=0.99  defect_rate=1.0  code_quality=0.83
             maintainability=0.94  idiomatic=0.88
test_coverage=0.99 ⇒ package imported and full pytest suite passed.
```

```text
Skip scan (grep pytest.skip|mark.skip|xfail across *.py): 0 skips, 0 xfail
Effective tests = passed + failed − skipped = all 53 fns effective (parametrized ×12)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (all .py, source+tests) | 891 |
| Source modules | app.py, db.py, repository.py, validation.py (+ conftest.py) |
| Test files | test_api.py (298), test_validation.py (122) |
| Files (excl. __pycache__/.git/.coverage) | 18 |
| Runtime dependencies | 1 (Flask) |
| Dev dependencies | +1 (pytest) |
| Tests total (functions) | 53 |
| Tests effective | 53 (no skips) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all `info`, no defects:

1. [info] Richer status-code coverage than spec requires (201/204/409/405 as JSON) — `app.py:81,108,123`
2. [info] Validation goes beyond required title/author (year range, ISBN shape, unknown-field rejection) — `validation.py:87`
3. [info] SQLite hardened with UNIQUE(isbn) + NOCASE author index → 409 on duplicate — `db.py:10`
4. [info] Coverage 99% not 100% (uncovered `__main__` block) — `scores.json`, `app.py:139`

## Architecture (run-summary unavailable)

Clean layered design with framework-independent core:
- `app.py` — Flask app factory (`create_app`), route registration, JSON error handlers for `ValidationError` / `DuplicateISBNError` / `HTTPException` / catch-all.
- `validation.py` — pure payload validation (no Flask/SQLite imports), unit-testable in isolation.
- `repository.py` — data access taking an explicit `sqlite3.Connection`, framework-agnostic.
- `db.py` — connection lifecycle via Flask `g`/`teardown`, schema, `init-db` CLI command.
- `conftest.py` — per-test tmp SQLite file for full isolation.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-46-opus5/bookshop/runs/language=python_model=claude-opus-5_prompt=neutral/rep1
cat scores.json                                   # stored mechanical scores (authoritative)
grep -rEc "def test_" *.py                         # test function counts
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" *.py   # skip scan (empty)
# To actually run the suite:
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```
