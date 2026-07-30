# Evaluation: agent=codex effort=medium model=gpt-5.6-terra prompt=neutral · rep 1

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-terra, effort=medium, prompt=neutral, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 3 passed / 0 failed / 0 skipped (3 effective)
- **Build:** pass — from scores.json (defect_rate=1.0, test_coverage=0.95)
- **Lint:** pass — code_quality=0.79 (from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

Scores read from `scores.json` (inline gate; no re-run):
`test_coverage=0.95`, `defect_rate=1.0`, `code_quality=0.789`,
`maintainability=0.863`, `idiomatic=0.85`, `token_efficiency=0.022`.
`test_coverage=0.95` and `defect_rate=1.0` ⇒ build succeeded and all tests passed.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:41` `create_book`, INSERT at `:47`, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:55` `list_books`, `SELECT * FROM books ORDER BY id` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:57-63` filters `WHERE author = ?` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:66` `get_book`, 404 via `not_found()` at `:70` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:73` `update_book`, UPDATE at `:81`, 404 if absent |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:88` `delete_book`, 204 / 404 on rowcount |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:6,105-114` stdlib `sqlite3`, schema `:12` |
| R8 | JSON responses + HTTP status codes | ✓ implemented | `jsonify` throughout; 201/200/204/400/404 used |
| R9 | Validation: title & author required | ✓ implemented | `app.py:126-136` `validated_book_payload`, 400 on missing |
| R10 | GET /health health check | ✓ implemented | `app.py:37-39` returns `{"status":"ok"}`, 200 |
| R11 | README with setup/run instructions | ✓ implemented | `README.md` setup, endpoints, tests sections |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | `test_app.py` 3 tests, `test_coverage=0.95` |

No enhancements beyond spec of note; `year`/`isbn` type validation is a reasonable
addition consistent with the spec.

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: test_coverage=0.95, defect_rate=1.0  => build + all tests passed
Skips: grep for pytest.skip/mark.skip/xfail in test_app.py => 0
Tests: 3 def test_ functions, all effective (0 skipped)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 211 (app.py 160, test_app.py 51) |
| Files | 11 |
| Dependencies | 2 (Flask, pytest) |
| Tests total | 3 |
| Tests effective | 3 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All 12 requirements implemented, all tests pass, no skipped/disabled tests,
no build/lint failures. `findings.jsonl` is empty.

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=medium_language=python_model=gpt-5.6-terra_prompt=neutral/rep1"
cat scores.json
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py
grep -cE "^\s*def test_" test_app.py
# to run tests locally (optional):
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && python3 -m pytest -q
```
