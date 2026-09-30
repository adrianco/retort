# Evaluation: effort=high_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, effort=high, prompt=neutral
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass — from `test_coverage=0.95`, `defect_rate=1.0` (scores.json)
- **Lint:** pass — `code_quality=0.83` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

Stored scores (scores.json, computed by retort's scorers — not re-run):
`test_coverage=0.95`, `code_quality=0.833`, `defect_rate=1.0`, `maintainability=0.975`, `idiomatic=0.87`, `token_efficiency=0.027`.
`defect_rate=1.0` and `test_coverage=0.95` confirm the build imported and all tests passed; the 0.95 is line coverage, not a pass-rate shortfall (uncovered lines are the server bootstrap and the last-resort 500 guard).

The neutral prompt factor (`prompts/neutral.md`) prescribes no methodology beyond "include tests that demonstrate the implementation meets the requirements" — no additional `P*` requirements over the pinned `REQUIREMENTS.json`.

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 items, fixed denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates (title, author, year, isbn) | ✓ implemented | `app.py:205 _create`; test `test_create_and_get_book` (tests/test_api.py:54) |
| R2 | GET /books lists all | ✓ implemented | `app.py:218 _list`; test `test_list_and_author_filter` (tests/test_api.py:90) |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:223-227` (COLLATE NOCASE); test tests/test_api.py:96-99 |
| R4 | GET /books/{id} single (404 if absent) | ✓ implemented | `app.py:234 _get`, `app.py:198-201 _fetch` 404; test tests/test_api.py:61, 127 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:237 _update`; test `test_update_book` (tests/test_api.py:102) |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:250 _delete`; test `test_delete_book` (tests/test_api.py:118) |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:9,16-24,106` sqlite3 + persistent file; test `test_data_persists_across_app_instances` (tests/test_api.py:135) |
| R8 | JSON responses + correct status codes | ✓ implemented | `app.py:124-131 _respond`; 201/200/204/400/404/405/413 across handlers |
| R9 | Validation: title & author required | ✓ implemented | `app.py:49-82 validate_book`; test `test_create_requires_title_and_author` (tests/test_api.py:66) |
| R10 | GET /health | ✓ implemented | `app.py:140-142`; test `test_health` (tests/test_api.py:48) |
| R11 | README with setup + run instructions | ✓ implemented | `README.md` (Setup/Run/Endpoints/Tests sections) |
| R12 | ≥ 3 unit/integration tests | ✓ implemented | 12 tests in tests/test_api.py; `test_coverage=0.95 > 0` |

## Build & Test

Not re-run — stored scores used per skill guidance.

```text
scores.json: test_coverage=0.95, defect_rate=1.0  ⇒ build imported, 12/12 tests passed
code_quality=0.833  ⇒ lint pass
```

Test command (for reference, not executed here):

```text
python -m pytest        # 12 tests, 0 skipped
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 421 (app.py 276 + tests 145) |
| Files | 5 (app.py, README.md, requirements.txt, tests/__init__.py, tests/test_api.py) |
| Dependencies | 1 (pytest, test-only) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top 5 by severity (full list in `findings.jsonl`) — all info-level, no defects:

1. [info] Framework-free WSGI + sqlite3 implementation with no runtime dependencies
2. [info] Handles 405/Allow, 413 oversized-body, and aggregated 400 validation beyond spec
3. [info] test_coverage=0.95 (not 1.0) — uncovered lines are bootstrap + 500 guard
4. [info] PUT performs full-record replacement (documented in README)

## Reproduce

```bash
cd experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=high_language=python_model=claude-sonnet-5-5_prompt=neutral/rep1
cat scores.json                                  # stored mechanical scores
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" tests/   # skip count (0)
grep -rE "^def test_" tests/test_api.py | wc -l  # test count (12)
python -m pytest                                 # optional re-run
```
