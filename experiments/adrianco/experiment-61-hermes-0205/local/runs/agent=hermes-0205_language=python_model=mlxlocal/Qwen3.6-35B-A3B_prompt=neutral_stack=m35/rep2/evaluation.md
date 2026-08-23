# Evaluation: hermes-0205 · python · Qwen3.6-35B-A3B · neutral · m35 · rep 2

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlxlocal/Qwen3.6-35B-A3B, prompt=neutral, stack=m35
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 14 passed / 0 failed / 0 skipped (14 effective) — from `_agent_stdout.log`; `test_coverage=0.97`
- **Build:** pass — `defect_rate=1.0` from `scores.json` (no re-run)
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** run-summary skill unavailable (not registered this session) — architecture summarized inline below
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low, 1 info)

## Requirements

Pinned list from `local/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:64-90` inserts all four fields, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:93-106` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:99-102` `WHERE author LIKE ?` |
| R4 | GET /books/{id} single book (404 if absent) | ✓ implemented | `app.py:109-116` returns 404 when None |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:119-149` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:152-162` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:3,15,29-44` sqlite3 + schema |
| R8 | JSON responses with correct status codes | ✓ implemented | `jsonify` + 201/200/404/400 throughout |
| R9 | Validation: title and author required | ✓ implemented | `app.py:74-77` (and PUT `134-137`) → 400 |
| R10 | GET /health health check | ✓ implemented | `app.py:58-61` returns `{"status":"ok"}` 200 |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — setup, run, testing, curl examples |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` — 14 tests, `test_coverage=0.97` |

## Build & Test

Not re-run — stored mechanical scores used per skill guidance.

```text
scores.json: test_coverage=0.97  defect_rate=1.0  code_quality=0.8333
_agent_stdout.log: "Test results: 14/14 passed"
skip scan (grep pytest.skip|mark.skip|xfail on test_app.py): 0
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 169 |
| Lines of code (test_app.py) | 176 |
| Source files | 4 (app.py, test_app.py, requirements.txt, README.md) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 14 |
| Tests effective | 14 |
| Skip ratio | 0% |
| Agent API calls / tokens | 8 calls / 178,606 total (32,441 in · 4,853 out) |

## Architecture (inline — run-summary unavailable)

Single-module Flask app (`app.py`): request-scoped SQLite connection via `get_db()`/`g` with WAL, teardown-closed; `init_db()` creates the `books` table; six routes (health + full CRUD) plus a `book_to_dict` serializer. Tests (`test_app.py`) use a `tempfile` DB fixture and a Flask `test_client`, grouped into per-endpoint classes covering success and error paths (missing title/author, no body, 404s, author filter).

## Findings

Full list in `findings.jsonl`. Nothing at medium or above.

1. [low] `year` field is not type-validated (`app.py:79`) — non-integer year persists as text; spec mandates only title/author validation.
2. [low] `init_db()` runs as an import side effect creating `books.db` in cwd (`app.py:166`).
3. [info] No pagination on GET /books (`app.py:104`) — enhancement only, not required.

## Reproduce

```bash
cd "experiments/adrianco/experiment-61-hermes-0205/local/runs/agent=hermes-0205_language=python_model=mlxlocal/Qwen3.6-35B-A3B_prompt=neutral_stack=m35/rep2"
cat scores.json                 # stored mechanical scores (build/test not re-run)
grep -cE "def test_" test_app.py
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l
```
