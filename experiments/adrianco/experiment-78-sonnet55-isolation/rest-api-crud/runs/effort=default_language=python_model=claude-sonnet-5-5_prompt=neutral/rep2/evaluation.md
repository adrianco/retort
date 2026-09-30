# Evaluation: effort=default_language=python_model=claude-sonnet-5-5_prompt=neutral · rep 2

## Summary

- **Factors:** language=python, model=claude-sonnet-5-5, prompt=neutral, effort=default
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 7 passed / 0 failed / 0 skipped (7 effective)
- **Build:** pass — `defect_rate=1.0` from scores.json (build + tests succeeded)
- **Lint:** pass — `code_quality=0.79` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Scores read from `scores.json` (inline gate, not re-run): `test_coverage=0.95`,
`defect_rate=1.0`, `code_quality=0.789`, `maintainability=0.917`, `idiomatic=0.78`,
`token_efficiency=0.043`. A stdlib-only WSGI + `sqlite3` service that implements the
full CRUD spec and passes every test.

## Requirements

Checklist is the pinned `rest-api-crud/REQUIREMENTS.json` (12 items, constant denominator).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:100 create()` INSERT; `test_app.py:30 test_create_and_get` → 201 |
| R2 | GET /books lists all books | ✓ implemented | `app.py:114 list()`; `test_app.py:43` len == 2 |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:116-118` WHERE author=?; `test_app.py:47` filter returns only Emma |
| R4 | GET /books/{id} single book | ✓ implemented | `app.py:123 get()` (404 if absent); `test_app.py:33`, `test_app.py:62` → 404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `app.py:127 update()`; `test_app.py:51 test_update` → 200/400/404 |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `app.py:143 delete()`; `test_app.py:59 test_delete` → 200 then 404 |
| R7 | Data stored in SQLite | ✓ implemented | `app.py:5,13-22` sqlite3 on-disk `books.db` (`BOOKS_DB` overridable) |
| R8 | JSON responses + status codes | ✓ implemented | `app.py:57-63` json.dumps + Content-Type; 201/200/400/404/405 |
| R9 | Validation: title & author required | ✓ implemented | `app.py:31-36 validate()`; `test_app.py:36 test_validation` → 400 |
| R10 | GET /health | ✓ implemented | `app.py:68`; `test_app.py:26 test_health` → 200 `{"status":"ok"}` |
| R11 | README with setup/run | ✓ implemented | `README.md:1-18` Run + Test + Endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | 7 tests in `test_app.py`; `test_coverage=0.95 > 0` |

## Build & Test

Not re-run — mechanical scores read from `scores.json` (per evaluate-run policy).
The agent's own run log confirms the suite:

```text
venv/bin/python -m pytest -q
.......                                                                  [100%]
7 passed in 0.02s
```

- `test_coverage=0.95` (tests executed, near-full line coverage)
- `defect_rate=1.0` (build + tests succeeded)

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 226 (app.py 154, test_app.py 72) |
| Files (source) | 3 (app.py, test_app.py, README.md) |
| Runtime dependencies | 0 (stdlib only) |
| Tests total | 7 |
| Tests effective | 7 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; no defects:

1. [info] Method-not-allowed handling (405) beyond spec — `app.py:69,75,85`
2. [info] Malformed-JSON and unknown-route tests beyond the 3-test minimum — `test_app.py:66`
3. [info] Stricter-than-required type validation on year/isbn — `app.py:37-44`

## Reproduce

```bash
cd "experiments/adrianco/experiment-78-sonnet55-isolation/rest-api-crud/runs/effort=default_language=python_model=claude-sonnet-5-5_prompt=neutral/rep2"
cat scores.json                                   # mechanical scores (not re-run)
cat ../../../REQUIREMENTS.json                     # pinned 12-item checklist
python -m pytest -q                                # 7 passed (agent log: "7 passed in 0.02s")
```
