# Evaluation: language=python·model=sonnet-5·prompt=bdd · rep 1

## Summary

- **Factors:** language=python, model=sonnet-5, prompt=bdd
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — `test_coverage=0.96`, `defect_rate=1.0` from `scores.json` (build + tests ran)
- **Lint:** pass — `code_quality=0.83` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app/main.py:37` `create_book`, INSERT + 201 |
| R2 | GET /books lists all | ✓ implemented | `app/main.py:50` `list_books`, SELECT * |
| R3 | GET /books ?author= filter | ✓ implemented | `app/main.py:55-59` `LIKE %..% COLLATE NOCASE` |
| R4 | GET /books/{id}, 404 if absent | ✓ implemented | `app/main.py:65-70`, raises 404 when row is None |
| R5 | PUT /books/{id} updates | ✓ implemented | `app/main.py:73-88`, UPDATE + 404 guard |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app/main.py:91-100`, DELETE + 204 / 404 guard |
| R7 | SQLite / embedded DB | ✓ implemented | `app/database.py:14` `CREATE TABLE books`, `sqlite3` |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/404/204 across handlers; validation → 422 (see finding) |
| R9 | title & author required | ✓ implemented | `app/schemas.py:7-17` min_length=1 + non-blank validator |
| R10 | GET /health | ✓ implemented | `app/main.py:32-34` returns `{"status":"ok"}` |
| R11 | README setup/run instructions | ✓ implemented | `README.md` Setup/Run/Tests sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 12 tests, `test_coverage=0.96` |

## Build & Test

Mechanical scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.96   -> build + tests executed and passed
defect_rate   = 1.00   -> build+test succeeded
code_quality  = 0.83   -> lint/quality
token_efficiency = 1.00
maintainability  = 0.27
idiomatic        = 0.58
```

Agent's own report (`_agent_stdout.log`): "Implementation is complete and all 12 tests pass." 12 test functions, 0 skips detected.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 342 (app 155, tests 187) |
| Files | 8 (`.py`, excl. `__pycache__`) |
| Dependencies | 5 (fastapi, uvicorn, pydantic, pytest, httpx) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build/test | pass (test_coverage=0.96) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Validation errors return 422, not the 400 suggested by the spec (`tests/test_books.py:33`) — idiomatic FastAPI, still a correct rejection.
2. [info] `init_db()` runs on every request via the `get_db` dependency (`app/main.py:13-19`).
3. [info] BDD prompt fully honored — Given/When/Then structure and behavioral test names throughout.

No critical/high/medium findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd experiment-15-sonnet5/rest-api/runs/language=python_model=sonnet-5_prompt=bdd/rep1
cat scores.json                                  # mechanical scores (build/test/lint)
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" tests/ --include="*.py"
grep -rE "^def test_" tests/*.py | wc -l         # 12
# to actually run tests (not required for eval):
# source .venv/bin/activate && pytest -v
```
