# Evaluation: agent=hermes-local language=python prompt=none stack=s1 · rep 3

## Summary

- **Factors:** language=python, agent=hermes-local, framework=unknown (Flask), prompt=none, stack=s1
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 16 passed / 0 failed / 0 skipped (16 effective)
- **Build:** pass — from `scores.json` (`test_coverage=0.97`, `defect_rate=1.0`)
- **Lint:** pass — `code_quality=0.7889`, `idiomatic=0.84` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:66-101` create_book, persists title/author/year/isbn |
| R2 | GET /books lists all | ✓ implemented | `app.py:106-119` list_books |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:112-115` `WHERE author LIKE ?` (substring) |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:124-131`, 404 at :130 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:136-174` update_book |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:179-189` delete_book |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:1,13,29` sqlite3, `books.db` table |
| R8 | JSON + appropriate status codes | ✓ implemented | 201/200/400/404 across handlers, all `jsonify(...)` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:76-79` blank-string checks → 400 |
| R10 | GET /health | ✓ implemented | `app.py:58-61` returns `{status: ok}` 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup, Usage, Testing sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 16 tests; `test_coverage=0.97` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill):

```text
test_coverage = 0.97   # build + tests executed; ~97% coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.7889
maintainability = 1.0
idiomatic     = 0.84
```

Agent self-report (`_agent_stdout.log`): "Test results: 16/16 passed". Skip scan (`grep pytest.skip|xfail`) = 0.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 396 (app.py 196, test_app.py 200) |
| Files | 12 (incl. runtime/coverage artifacts) |
| Dependencies | 2 (flask, pytest) |
| Tests total | 16 |
| Tests effective | 16 |
| Skip ratio | 0% |
| Build duration | n/a (scores cached) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Flask runs with `debug=True` — `app.py:196`
2. [info] Author filter is a substring `LIKE` match, not exact — `app.py:113-114`

No critical, high, or medium findings. This is a clean, spec-complete run.

## Reproduce

```bash
cd "experiment-27-sampling-ff/bookshop/runs/agent=hermes-local_language=python_prompt=none_stack=s1/rep3"
cat scores.json                       # cached mechanical scores (no re-run)
grep -rEn "pytest\.skip|xfail" . --include="*.py" | wc -l   # skip count = 0
# to re-run tests independently:
pip install -r requirements.txt && pytest test_app.py -v
```
