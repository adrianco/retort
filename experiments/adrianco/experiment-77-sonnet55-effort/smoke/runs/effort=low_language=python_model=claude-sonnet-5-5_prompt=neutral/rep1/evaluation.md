# Evaluation: effort=low_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=low (agent/framework unknown)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, 12 items)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — `defect_rate=1.0`, `test_coverage=0.93` (line coverage) from `scores.json`
- **Build:** pass (not re-run — `defect_rate=1.0` from `scores.json`)
- **Lint:** pass — `code_quality=0.79` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 0 low, 1 info)

The neutral prompt factor adds no extra checkable requirement (it only says to use whatever approach and include tests), so the spec is TASK.md / `REQUIREMENTS.json` alone — no `P*` items.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `app.py:84-93` INSERT + 201; test `test_create_and_get` |
| R2 | GET /books lists all books | ✓ implemented | `app.py:78-83` SELECT * ORDER BY id |
| R3 | GET /books supports ?author= filter | ✓ implemented | `app.py:77,81-82`; test `test_list_filter` |
| R4 | GET /books/{id} single book by id | ✓ implemented | `app.py:95-102`, 404 at `app.py:100` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `app.py:103-112`; test `test_update_delete` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `app.py:113-116` (204); test `test_update_delete` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:13-22` `init_db` CREATE TABLE books |
| R8 | JSON responses + appropriate status codes | ✓ implemented | `app.py:51-57` `_send`; 201/200/400/404/405/204 throughout |
| R9 | Validation: title and author required | ✓ implemented | `app.py:25-43` `validate`; test `test_validation` |
| R10 | GET /health endpoint | ✓ implemented | `app.py:73-74` returns `{"status":"ok"}`; test `test_health` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` (run/endpoints/test sections) |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/test_app.py` 5 tests, `test_coverage=0.93` |

## Build & Test

Not re-run — mechanical scores were read from `scores.json` (inline gate output), per the evaluate-run skill.

```text
scores.json
test_coverage = 0.93   (line coverage; tests executed and passed)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.789
maintainability = 0.952
idiomatic     = 0.38   (haiku judge, cached in .idiomatic_cache.json)
token_efficiency = 0.023
```

5 test functions, 0 skips (`grep pytest.skip|xfail` → 0).

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 136 (app.py) + 67 (tests) = 203 |
| Files (source) | 4 (app.py, tests/test_app.py, README.md, TASK.md) |
| Dependencies | 0 runtime (stdlib only); pytest for tests |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [medium] Single SQLite connection shared across `ThreadingHTTPServer` threads without a lock — `app.py:14,129`
2. [info] PUT requires a full valid body (no partial update) — `app.py:104-110` (matches spec/README)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-77-sonnet55-effort/smoke/runs/effort=low_language=python_model=claude-sonnet-5-5_prompt=neutral/rep1
cat scores.json                                              # stored mechanical scores (no re-run)
cat ../../../REQUIREMENTS.json                               # pinned 12-item checklist
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" tests/    # skip count -> 0
grep -rE "^def test_" tests/test_app.py | wc -l              # test count -> 5
wc -l app.py tests/test_app.py                               # LOC
```
