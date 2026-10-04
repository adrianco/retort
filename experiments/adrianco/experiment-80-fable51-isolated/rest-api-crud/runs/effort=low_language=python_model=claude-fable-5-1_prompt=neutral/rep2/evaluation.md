# Evaluation: effort=low_language=python_model=claude-fable-5-1_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-fable-5-1, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** all passed / 0 failed / 0 skipped (10 test functions, one 6-way parametrized ⇒ ~15 effective cases)
- **Build:** pass — from `scores.json` `defect_rate=1.0` (build+test succeeded)
- **Lint:** pass — `code_quality=0.79` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

Scores read from `{run_dir}/scores.json` (inline gate eval; run not yet in
`retort.db`): `test_coverage=0.91`, `code_quality=0.7889`, `defect_rate=1.0`,
`maintainability=0.9964`, `idiomatic=0.87`, `token_efficiency=0.0595`. Build/test
were NOT re-run per skill guidance.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:156-158` validate+`store.create`; `test_app.py:test_create_and_get` |
| R2 | GET /books lists all | ✓ implemented | `app.py:153-155` `store.list`; `test_app.py:test_list_and_author_filter` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:154` + `app.py:51-55` `WHERE author=? COLLATE NOCASE`; `test_list_and_author_filter` |
| R4 | GET /books/{id} by id (404) | ✓ implemented | `app.py:163-164,173-175`; `test_create_and_get`, `test_not_found_and_method_not_allowed` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:165-166` + `app.py:68-74`; `test_app.py:test_update` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:167-170` (204) + `app.py:76-79`; `test_app.py:test_delete` |
| R7 | SQLite / embedded DB | ✓ implemented | `BookStore` `sqlite3.connect` `app.py:21-37`; `make_server` default `books.db` `app.py:195` |
| R8 | JSON responses + status codes | ✓ implemented | `_send`/`_error` `app.py:118-128`; 201/200/204/400/404/405 across `_route` |
| R9 | Validation: title+author required | ✓ implemented | `validate_book` `app.py:91-94`; `test_app.py:test_create_validation` (6 cases) |
| R10 | GET /health | ✓ implemented | `app.py:148-151` returns `{"status":"ok"}`; `test_app.py:test_health` |
| R11 | README with setup + run | ✓ implemented | `README.md` — Setup/Run/Endpoints/Test sections |
| R12 | ≥3 unit/integration tests | ✓ implemented | 10 `def test_` funcs in `test_app.py`; `test_coverage=0.91` |

No prompt-factor requirements: `prompt=neutral` is not a `prompts/<level>.md`
instruction set for this experiment (neutral phrasing of the base ask).

## Build & Test

Not re-run — stored scores used (skill Step 2).

```text
scores.json
test_coverage = 0.91   (tests executed and passed)
defect_rate   = 1.0    (build + test succeeded)
code_quality  = 0.7889
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 336 (app.py 217, test_app.py 119) |
| Files | 4 tracked (app.py, test_app.py, README.md, TASK.md) |
| Dependencies | 0 runtime (stdlib only); `pytest` for tests |
| Tests total | 10 functions (~15 cases with parametrize) |
| Tests effective | ~15 (0 skipped) |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

None. All 12 requirements implemented with test coverage, no skipped/disabled
tests, build+test pass. `findings.jsonl` is empty.

## Reproduce

```bash
cd "runs/effort=low_language=python_model=claude-fable-5-1_prompt=neutral/rep2"
cat scores.json
grep -cE "^def test_" test_app.py
grep -rE "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py | wc -l
wc -l app.py test_app.py
```
