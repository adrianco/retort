# Evaluation: agent=hermes-0205 · python · Qwen3-Coder-30B-A3B-Instruct-4bit · q4 · neutral · rep 5

## Summary

- **Factors:** language=python, agent=hermes-0205, model=mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit, stack=q4, prompt=neutral
- **Status:** ok (served app implements only a fraction of the spec)
- **Requirements:** 5/12 implemented, 1 partial, 6 missing (requirement_coverage = 0.4167)
- **Tests:** partial — `test_coverage=0.25` from scores.json (integration tests hit endpoints the served app lacks)
- **Build:** pass (imports succeed) — from scores.json defect_rate=1.0
- **Lint:** pass — code_quality=0.8333 from scores.json
- **Architecture:** see `summary/`
- **Findings:** 8 items in `findings.jsonl` (0 critical, 5 high, 2 medium, 1 test_failure high)

## Second-opinion verdict

This is a re-check of a prior evaluation that scored `requirement_coverage=0.4167` and
flagged R1, R4, R5, R6, R9 as NOT met. **All five claims are CONFIRMED.** The first
evaluator was correct on every one — none invented a missing feature.

The root cause: there are two files. `main.py` is the **served app** (it holds the
`uvicorn.run("main:app", ...)` entrypoint at main.py:35) and exposes only
`GET /health` and `GET /books`. `book_api.py` contains full CRUD functions
(`create_book`, `get_book_by_id`, `update_book`, `delete_book`) but is a standalone
script whose `__main__` just prints a demo — **`main.py` never imports `book_api`**
(`grep book_api *.py` → no matches) and none of those functions are bound to a route.
So over HTTP the CRUD operations do not exist.

| Claim (first eval said MISSING) | Re-check | Evidence |
|----|----|----|
| R1 POST /books | **CONFIRMED missing** | no `@app.post` in main.py; create_book at book_api.py:24 unrouted, book_api not imported |
| R4 GET /books/{id} | **CONFIRMED missing** | no `@app.get('/books/{id}')`; get_book_by_id at book_api.py:57 unrouted |
| R5 PUT /books/{id} | **CONFIRMED missing** | no `@app.put`; update_book at book_api.py:70 unrouted |
| R6 DELETE /books/{id} | **CONFIRMED missing** | no `@app.delete`; delete_book at book_api.py:114 unrouted |
| R9 input validation | **CONFIRMED missing** | no POST route, no Pydantic model; NOT NULL at book_api.py:15 never reached over HTTP |

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✗ missing | no `@app.post`; create_book unrouted (book_api.py:24), book_api not imported |
| R2 | GET /books lists all | ✓ implemented | main.py:26 `@app.get('/books')` returns all rows |
| R3 | GET /books ?author= filter | ✗ missing | main.py:27 get_books() has no author param; SELECT * unconditional (main.py:30) |
| R4 | GET /books/{id} | ✗ missing | no route; get_book_by_id unrouted (book_api.py:57) |
| R5 | PUT /books/{id} | ✗ missing | no route; update_book unrouted (book_api.py:70) |
| R6 | DELETE /books/{id} | ✗ missing | no route; delete_book unrouted (book_api.py:114) |
| R7 | SQLite storage | ✓ implemented | main.py:7-20 sqlite3 + books.db table |
| R8 | JSON responses w/ status codes | ~ partial | GET /books returns raw tuples (main.py:33); only default 200, no 201/404/400 |
| R9 | Validation: title/author required | ✗ missing | no POST route, no Pydantic; NOT NULL never reached over HTTP |
| R10 | GET /health | ✓ implemented | main.py:22 `@app.get('/health')` → `{"status":"healthy"}` |
| R11 | README with setup/run | ✓ implemented | README.md documents install + `uvicorn main:app` |
| R12 | ≥3 tests | ✓ implemented | test_book_api.py (9 funcs), test_db.py, test_simple.py; test_coverage=0.25 > 0 |

## Build & Test

Scores read from `scores.json` (not re-run):

```text
test_coverage = 0.25    # integration tests target endpoints the served app lacks -> failures
defect_rate   = 1.0     # imports/build ok
code_quality  = 0.8333
maintainability = 0.8509
idiomatic     = 0.48
```

`test_book_api.py` starts a real uvicorn server and calls POST/GET-by-id/PUT/DELETE
(lines 23, 55, 74, 98); those hit 404/405 because `main:app` serves only
`GET /health` and `GET /books`. Zero explicit skips.

## Metrics

| Metric | Value |
|--------|-------|
| Source files (py) | 6 (main.py, book_api.py, 3 test files, check_env.py) |
| Served routes | 2 (GET /health, GET /books) |
| CRUD functions unrouted | 4 (in book_api.py) |
| Tests total (functions) | ~11 |
| Skips | 0 |
| test_coverage | 0.25 |

## Findings

Top by severity (full list in `findings.jsonl`):

1. [high] R1 — POST /books not exposed by the served app
2. [high] R4 — GET /books/{id} not exposed by the served app
3. [high] R5 — PUT /books/{id} not exposed by the served app
4. [high] R6 — DELETE /books/{id} not exposed by the served app
5. [high] R9 — no input validation in the served API
6. [high] test-fail-1 — integration tests exercise endpoints main:app does not expose
7. [medium] R3 — ?author= filter absent from served GET /books
8. [medium] R8 — GET /books returns raw tuples, no 201/404/400

## Reproduce

```bash
cd runs/agent=hermes-0205_language=python_model=mlxlocal/mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit_prompt=neutral_stack=q4/rep5
grep -n "@app\." main.py            # only /health and /books (GET)
grep -rn "book_api" *.py            # no matches -> book_api never imported
cat scores.json                     # test_coverage=0.25
```
