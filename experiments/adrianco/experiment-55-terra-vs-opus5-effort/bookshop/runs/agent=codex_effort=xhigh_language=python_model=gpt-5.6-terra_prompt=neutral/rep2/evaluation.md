# Evaluation: agent=codex effort=xhigh language=python model=gpt-5.6-terra prompt=neutral · rep 2

## Summary

- **Factors:** language=python, agent=codex, model=gpt-5.6-terra, prompt=neutral, effort=xhigh, framework=Flask
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective)
- **Build:** pass — from `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.62`, `maintainability=0.91` (scores.json); no linter re-run
- **Architecture:** single-module Flask app factory + SQLite; `summary/` skill unavailable in this session
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:51` `create_book` inserts title/author/year/isbn, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:71` `list_books` returns full collection |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:74-79` filters by `author` query param; `test_app.py:45` |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:82` `get_book`, 404 when absent (`app.py:85`) |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:89` `update_book`, merges fields, 404 if absent |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:122` `delete_book` returns 204; `test_app.py:65` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:13` SCHEMA, `app.py:136` `sqlite3.connect` |
| R8 | JSON responses + status codes | ✓ implemented | 201/200/404/400/204 across routes; `error_response` `app.py:203` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:168` `validate_book_fields`; `test_app.py:69` |
| R10 | GET /health | ✓ implemented | `app.py:47` returns `{"status":"ok"}`; `test_app.py:30` |
| R11 | README with setup/run | ✓ implemented | `README.md` — venv, pip install, run, endpoints, tests |
| R12 | ≥3 tests | ✓ implemented | `test_app.py` has 5 test methods; `test_coverage=0.92` |

## Build & Test

Scores read from `scores.json` (not re-run per evaluate-run skill):

```text
test_coverage = 0.92   (build succeeded + tests executed and passed)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.62
maintainability = 0.91
idiomatic     = 0.58
token_efficiency = 0.031
```

Note: the agent's own final verification/cleanup shell command was rejected by
the sandbox (`rm -f style commands are not permitted`, see `_agent_stderr.log`),
but this did not affect the delivered code — tests still pass.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (app.py) | 211 |
| Lines of code (test_app.py) | 77 |
| Files (excl. caches) | 12 |
| Dependencies | 1 (Flask) |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Partial test coverage (0.92) — error/validation branches not all exercised
2. [info] POST /books returns a Location header (beyond spec)
3. [info] Rich input validation beyond required title/author check

## Reproduce

```bash
cd "experiments/adrianco/experiment-55-terra-vs-opus5-effort/bookshop/runs/agent=codex_effort=xhigh_language=python_model=gpt-5.6-terra_prompt=neutral/rep2"
python -m unittest -v      # 5 tests
cat scores.json            # stored mechanical scores
```
