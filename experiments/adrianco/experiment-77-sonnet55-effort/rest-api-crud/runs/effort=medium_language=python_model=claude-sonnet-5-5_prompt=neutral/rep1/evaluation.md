# Evaluation: effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=medium (tooling: none)
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 8 passed / 0 failed / 0 skipped (8 effective)
- **Build:** pass — from `defect_rate=1.0` (retort.db / scores.json); no separate build step (stdlib only)
- **Lint:** pass — `code_quality=0.79` (scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

Scores read from `scores.json` (inline gate, not re-run): `test_coverage=0.94`, `defect_rate=1.0`, `code_quality=0.7889`, `maintainability=0.9333`, `idiomatic=0.84`, `token_efficiency=0.0291`. `defect_rate=1.0` ⇒ build + tests succeeded; `test_coverage=0.94` is line coverage over the 8 passing tests. The neutral prompt factor adds no checkable instruction beyond "include tests" (already R12), so no `P*` requirements apply.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:131` → `BookStore.create` (`app.py:36`); `test_create_and_get` |
| R2 | GET /books lists all | ✓ implemented | `app.py:132-134` → `BookStore.list` (`app.py:45`); `test_list_and_author_filter` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:133` parses `author`; `list(author)` `app.py:47-49`; `test_list_and_author_filter` |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:139-140,149-151`; `BookStore.get`; 404 path `app.py:150` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:141-142` → `BookStore.update` (`app.py:58`); `test_update` incl. 404 |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:143-145` → `BookStore.delete`; 204/404; `test_delete` |
| R7 | Stored in SQLite | ✓ implemented | `sqlite3` `BookStore` `app.py:18-30`; default file `books.db` `app.py:171` |
| R8 | JSON + correct status codes | ✓ implemented | `_send` `app.py:107`; 201/200/204/400/404/405/500 across `_route` |
| R9 | Validation: title & author required | ✓ implemented | `validate` `app.py:76-98`; `test_validation` (400 on missing/blank) |
| R10 | GET /health | ✓ implemented | `app.py:127`; `test_health` returns `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md` (setup, run, env vars, endpoints, tests) |
| R12 | ≥3 tests | ✓ implemented | 8 tests in `test_app.py`; `test_coverage=0.94` (> 0) |

## Build & Test

Scores were read from `scores.json` (skill step 2 — do NOT re-run the toolchain).

```text
defect_rate   = 1.0     # build + tests succeeded
test_coverage = 0.94    # line coverage over 8 passing tests
```

```text
8 test functions in test_app.py, 0 skipped/xfail:
  test_health, test_create_and_get, test_validation, test_invalid_json,
  test_list_and_author_filter, test_update, test_delete, test_unknown_route
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source, app.py) | 179 |
| Lines of code (test, test_app.py) | 86 |
| Files (excl. logs/pycache) | 6 (app.py, test_app.py, README.md, TASK.md, stack.json, scores.json) |
| Dependencies | 0 (stdlib only; pytest for tests) |
| Tests total | 8 |
| Tests effective | 8 |
| Skip ratio | 0% |
| Build duration | n/a (interpreted, no build step) |

## Findings

None. All 12 pinned requirements are implemented and exercised by passing tests; no skipped/disabled tests; no build/test/lint failures.

## Reproduce

```bash
cd "experiments/adrianco/experiment-77-sonnet55-effort/rest-api-crud/runs/effort=medium_language=python_model=claude-sonnet-5-5_prompt=neutral/rep1"
cat scores.json                                   # stored build/test/lint scores (not re-run)
grep -cE "^def test_" test_app.py                 # 8 tests
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # 0 skips
# (optional re-verify) python -m pytest test_app.py
```
