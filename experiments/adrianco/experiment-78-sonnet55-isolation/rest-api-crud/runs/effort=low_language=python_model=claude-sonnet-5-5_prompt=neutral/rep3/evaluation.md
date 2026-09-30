# Evaluation: effort=low_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`, R1–R12)
- **Tests:** 5 passed / 0 failed / 0 skipped (5 effective) — `test_coverage=0.92`, `defect_rate=1.0` from `scores.json`
- **Build:** pass — stdlib-only, no build step (import + tests succeeded)
- **Lint:** pass — `code_quality=0.79` from `scores.json`
- **Architecture:** see `summary/index.md`
- **Findings:** 0 items in `findings.jsonl`

## Requirements

Denominator fixed by `rest-api-crud/REQUIREMENTS.json`. The `neutral` prompt prescribes no methodology, so it adds no `P` requirements.

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:85 do_POST` → `validate` + INSERT; `test_app.py:34 test_crud_flow` |
| R2 | GET /books lists all | ✓ implemented | `app.py:73-79`; `test_app.py:56` asserts len==2 |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:74-76`; `test_app.py:51 test_author_filter` |
| R4 | GET /books/{id} single (404) | ✓ implemented | `app.py:80-83`; `test_app.py:37`, `:59 test_missing` |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:97 do_PUT`; `test_app.py:39` |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:111 do_DELETE`; `test_app.py:41` |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:12-20 init_db` sqlite3 table |
| R8 | JSON responses + status codes | ✓ implemented | `app.py:45-51 _send` sets `application/json`; 201/200/404/400 throughout |
| R9 | Validation: title & author required | ✓ implemented | `app.py:23-37 validate`; `test_app.py:45 test_validation` |
| R10 | GET /health | ✓ implemented | `app.py:71-72`; `test_app.py:30 test_health` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Run/Endpoints/Test sections |
| R12 | ≥3 tests | ✓ implemented | 5 tests in `test_app.py`; `test_coverage=0.92>0` |

## Build & Test

Scores read from `scores.json` (per skill Step 2 — build/test not re-run):

```text
test_coverage = 0.92   # tests executed and passed (line coverage 92%)
defect_rate   = 1.0    # build + test succeeded
code_quality  = 0.7889
maintainability = 0.9419
idiomatic     = 0.68
token_efficiency = 0.0363
```

Skip scan (`grep pytest.skip|mark.skip|xfail test_app.py`): 0 matches — no disabled tests.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 190 (app.py 129 + test_app.py 61) |
| Files (tracked source) | 3 (app.py, test_app.py, README.md) |
| Dependencies | 1 dev-only (pytest); runtime stdlib-only |
| Tests total | 5 |
| Tests effective | 5 |
| Skip ratio | 0% |
| Build duration | n/a (stdlib, no build) |

## Findings

None. All 12 pinned requirements implemented and exercised by tests; no skipped/disabled tests; build and tests passed.

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-78-sonnet55-isolation/rest-api-crud/runs/effort=low_language=python_model=claude-sonnet-5-5_prompt=neutral/rep3
cat scores.json                                  # stored mechanical scores
grep -cE "^def test_" test_app.py                # 5 tests
grep -rEc "pytest\.skip|@pytest\.mark\.skip|xfail" test_app.py   # 0 skips
# (build/test intentionally NOT re-run; scores.json is authoritative)
```
