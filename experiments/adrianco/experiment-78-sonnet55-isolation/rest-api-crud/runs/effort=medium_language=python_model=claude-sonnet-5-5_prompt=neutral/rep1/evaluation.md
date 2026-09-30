# Evaluation: effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=medium
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned REQUIREMENTS.json)
- **Tests:** 6 passed / 0 failed / 0 skipped (6 effective)
- **Build:** pass — import/collection succeeded (test_coverage=0.98, defect_rate=1.0 from retort.db)
- **Lint:** pass — code_quality=0.79 from retort.db (no separate lint re-run)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

Checklist is the pinned `REQUIREMENTS.json` (constant denominator across runs).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:87,117` `_create` INSERT; test_create_and_get |
| R2 | GET /books lists all | ✓ implemented | `app.py:85,105` `_list`; test_list_and_filter |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:107-110` parse_qs + WHERE author=? |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.py:92,134` `_get`, 404 at :140 |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:94,143` `_update`; test_update |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:96,162` `_delete`, 204/404; test_delete |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:5,13-21` sqlite3 + books table |
| R8 | JSON responses + status codes | ✓ implemented | `app.py:61-67` `_send`; 201/200/404/400/204 used |
| R9 | Validation: title & author required | ✓ implemented | `app.py:24-46` `validate`; test_validation |
| R10 | GET /health | ✓ implemented | `app.py:83-84` returns `{"status":"ok"}`; test_health |
| R11 | README with setup & run | ✓ implemented | `README.md` — Run/Endpoints/Test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_app.py` 6 tests, test_coverage=0.98 |

## Build & Test

Scores read from `retort.db` / `scores.json` (not re-run, per skill):

```text
test_coverage = 0.98   # build + all tests passed, 98% line coverage
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.79
requirement_coverage = 1.0
```

```text
6 pytest tests (test_app.py): health, create+get, validation, list+filter, update, delete
0 skipped / 0 xfail (grep of pytest.skip|mark.skip|xfail == 0)
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 256 (app.py 184 + test_app.py 72) |
| Files | 11 (incl. logs, .coverage, caches) |
| Dependencies | 0 runtime (stdlib only); pytest for tests |
| Tests total | 6 |
| Tests effective | 6 |
| Skip ratio | 0% |
| Run duration | 23.1s (from retort.db) |

## Findings

Top findings (full list in `findings.jsonl`) — all info-level, no defects:

1. [info] Thread-safe DB access via a global lock
2. [info] Zero-dependency stdlib implementation
3. [info] All SQL is parameterized (no injection surface)

## Reproduce

```bash
cd "experiments/adrianco/experiment-78-sonnet55-isolation/rest-api-crud/runs/effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored mechanical scores
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" . --include="*.py" | wc -l   # 0
python -m pytest                                  # (optional) 6 passed
```
