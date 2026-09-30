# Evaluation: effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=medium (agent/framework=unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 9 passed / 0 failed / 0 skipped (9 effective) — 5 test functions, one parametrized ×5
- **Build:** pass — `test_coverage=0.93`, `defect_rate=1.0` (from `scores.json`; build+tests ran and passed)
- **Lint:** pass — `code_quality=0.789` (from `scores.json`)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:68-75` INSERT + 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:81-83` SELECT all → 200 |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:77-80` `WHERE author = ?`; test `tests/test_api.py:53` |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `app.py:85-94` regex route, 404 on miss |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:95-101` UPDATE → 200 |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:102-104` DELETE → 204 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:5,17-24` `sqlite3` + `CREATE TABLE books` |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `app.py:107-134` STATUS map, JSON body; codes 200/201/204/400/404/405 |
| R9 | Validation: title and author required | ✓ implemented | `app.py:27-44` `validate()`; test `tests/test_api.py:57-63` |
| R10 | GET /health health check | ✓ implemented | `app.py:65-66` → `{"status":"ok"}` |
| R11 | README with setup and run instructions | ✓ implemented | `README.md` — Run/Test/Endpoints sections |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/test_api.py` — 5 functions (9 cases), `test_coverage=0.93` |

## Build & Test

Scores read from `scores.json` (not re-run, per skill guidance):

```text
test_coverage = 0.93   # build + tests executed and passed; 93% line coverage
defect_rate   = 1.0    # build+test succeeded
code_quality  = 0.789
maintainability = 0.935
idiomatic     = 0.55
token_efficiency = 0.041
```

Test suite (`tests/test_api.py`): in-process WSGI client, 5 functions — health, full CRUD lifecycle, list + author filter, parametrized validation (5 bad-body cases across POST and PUT), and missing/invalid-path handling. 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, app.py) | 143 |
| Test LOC | 69 |
| Files (source) | 8 (incl. artifacts); 3 authored (app.py, tests/test_api.py, README.md) |
| Dependencies | 0 runtime (stdlib only); pytest for tests |
| Tests total | 9 (5 functions, one parametrized ×5) |
| Tests effective | 9 |
| Skip ratio | 0% |
| Build duration | n/a (scores from archive) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Idiomatic score moderate (0.55) — hand-rolled WSGI dispatch vs. a framework
2. [info] Stdlib-only implementation (no web framework) — zero runtime dependencies
3. [info] PUT uses full-replace semantics and re-validates title/author

No requirement gaps, no test failures, no skipped tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-78-sonnet55-isolation/rest-api-crud/runs/effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral/rep3"
cat scores.json                      # stored mechanical scores (build/test/lint)
python -m pytest tests               # 9 tests pass
python app.py                        # serve on http://127.0.0.1:8000
```
