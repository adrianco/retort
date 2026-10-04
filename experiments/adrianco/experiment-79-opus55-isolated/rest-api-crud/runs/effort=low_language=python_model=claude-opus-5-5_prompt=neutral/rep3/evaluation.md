# Evaluation: rest-api-crud · effort=low language=python model=claude-opus-5-5 prompt=neutral · rep 3

## Summary

- **Factors:** language=python, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass (import/collection succeeded; test_coverage=0.91 from scores.json)
- **Lint:** pass — code_quality=0.79 from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `app.py:193-200` POST → `BookStore.create`; `test_create_and_get` |
| R2 | GET /books lists all | ✓ implemented | `app.py:190-192` → `BookStore.list`; `test_list_and_author_filter` |
| R3 | GET /books ?author= filter | ✓ implemented | `app.py:191` passes author; `app.py:102-105` `WHERE author = ? COLLATE NOCASE` |
| R4 | GET /books/{id} single | ✓ implemented | `app.py:205-206` → `get`; 404 at `app.py:221-222`; `test_create_and_get`/`test_not_found` |
| R5 | PUT /books/{id} update | ✓ implemented | `app.py:207-214` → `BookStore.update`; `test_update` |
| R6 | DELETE /books/{id} | ✓ implemented | `app.py:215-217` → `delete`, 204; `test_delete` |
| R7 | SQLite persistence | ✓ implemented | `app.py:61-133` `BookStore` on `sqlite3`, `CREATE TABLE books` |
| R8 | JSON + correct status codes | ✓ implemented | 201/200/204/404/422/409/405 across `_route`; `_send` sets `application/json` |
| R9 | Validation: title & author required | ✓ implemented | `app.py:33-40` `validate_book`; rejected via 422 (`test_create_validation`) — see finding on 422-vs-400 |
| R10 | GET /health | ✓ implemented | `app.py:184-187` returns `{"status":"ok"}`; `test_health` |
| R11 | README with setup/run | ✓ implemented | `README.md` — Setup, Run, Endpoints, Errors, Tests |
| R12 | ≥ 3 tests | ✓ implemented | 13 test methods in `test_app.py`; test_coverage=0.91 |

## Build & Test

Build/test not re-run — mechanical scores read from `scores.json` (inline gate output):

```text
scores.json: test_coverage=0.91, defect_rate=1.0, code_quality=0.79,
             maintainability=0.99, idiomatic=0.62, token_efficiency=0.054
```

`test_coverage=0.91` (>0) ⇒ the suite built and ran; `defect_rate=1.0` ⇒ build + tests
passed. 13 test methods discovered, 0 skips.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 277 (`app.py`) |
| Lines of code (tests) | 147 (`test_app.py`) |
| Files (source) | 3 (app.py, test_app.py, README.md) |
| Dependencies | 0 (stdlib only) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Coverage | 0.91 |

## Findings

Top findings (full list in `findings.jsonl`):

1. [low] Validation errors return 422 instead of the 400 the task illustrates (requirement still met — rejection occurs)
2. [info] Unique-isbn conflict handled with 409 (beyond spec)
3. [info] Request body size guard returns 413 (beyond spec)
4. [info] Thread-safe SQLite store (beyond spec)

## Reproduce

```bash
cd "experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=python_model=claude-opus-5-5_prompt=neutral/rep3"
cat scores.json                       # mechanical scores (not re-run)
grep -c "def test_" test_app.py       # 13 tests
grep -rEn "skip|xfail" test_app.py    # 0 skips
python3 -m unittest -v                # optional: re-run the suite
```
