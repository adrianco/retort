# Evaluation: effort=low language=c model=claude-haiku-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=c, model=claude-haiku-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 89 assertions across 9 test functions passed / 0 failed / 0 skipped (89 effective)
- **Build:** pass — `test_coverage=1.0` from `scores.json` (build + tests)
- **Lint:** pass — `code_quality=1.0` from `scores.json`; Makefile compiles with `-Wall -Wextra -Wpedantic`
- **Architecture:** see `summary/index.md`
- **Findings:** 4 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 4 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `src/api.c:create_book` → `store_create`; `test_create_get_and_validation` asserts 201 |
| R2 | GET /books lists all | ✓ implemented | `src/api.c:list_books` → `store_list(NULL)`; `test_list_and_author_filter` count==3 |
| R3 | GET /books ?author= filter | ✓ implemented | `src/http.c:query_param` + `src/db.c:store_list` `WHERE author = ?1 COLLATE NOCASE`; test filters to 2 |
| R4 | GET /books/{id} single + 404 | ✓ implemented | `src/api.c:get_book` returns 404 on rc==0; test asserts 200 and /books/999→404 |
| R5 | PUT /books/{id} updates | ✓ implemented | `src/api.c:update_book` → `store_update`; `test_update_and_delete` asserts 200, 404 for missing |
| R6 | DELETE /books/{id} deletes | ✓ implemented | `src/api.c:delete_book` → `store_delete`; test asserts 204 then 404 |
| R7 | Data stored in SQLite | ✓ implemented | `src/db.c` uses `sqlite3_*`, `CREATE TABLE books`, prepared statements |
| R8 | JSON responses + status codes | ✓ implemented | `src/http.c:write_response` sets `application/json`; 200/201/204/400/404/405/413/431/500 |
| R9 | Validation: title+author required | ✓ implemented | `src/api.c:validate_book` rejects missing/blank/non-string → 400; 11 invalid-body cases tested |
| R10 | GET /health | ✓ implemented | `src/api.c:api_handle` `/health` → `{"status":"ok"}`; `test_health` asserts 200 |
| R11 | README with setup/run | ✓ implemented | `README.md` documents deps, `make`/`make test`/run, env vars, endpoints |
| R12 | ≥3 unit/integration tests | ✓ implemented | `tests/test_all.c` — 9 test functions, 89 `CHECK` assertions; `test_coverage=1.0` |

No prompt-factor requirements (`prompt=neutral` carries no extra checklist beyond TASK.md).

## Build & Test

Build and tests were **not re-run** — stored mechanical scores from `scores.json`
stand in (per the evaluate-run skill):

```text
scores.json: {"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
              "maintainability": 0.679, "idiomatic": 0.6, "token_efficiency": 0.047}
```

- `test_coverage=1.0` ⇒ `make test` built the library + harness and all assertions passed.
- `defect_rate=1.0` ⇒ build+test succeeded.
- `code_quality=1.0` ⇒ clean under the compiler warnings configured in the Makefile.

Test harness (`tests/test_all.c`) covers: health (incl. 405), create/get/validation
(incl. 11 malformed bodies + rollback check), list + author filter (incl. `+`/`%20`
decoding and empty result), update/delete lifecycle, routing errors, the JSON parser
(valid + 10 malformed), HTTP head parsing, query-param decoding, and a real-socket
HTTP round-trip via `http_serve(max_connections=1)`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source + tests) | 1653 |
| Source files (src/ + tests/) | 14 |
| Dependencies | 1 (libsqlite3) |
| Tests total (functions / assertions) | 9 / 89 |
| Tests effective | 89 |
| Skip ratio | 0% |
| Build | pass (from scores.json) |

## Findings

Top findings (full list in `findings.jsonl`) — all informational; this is a clean run:

1. [info] Strict hand-written JSON parser beyond spec (`src/json.c`)
2. [info] Validation richer than required: length caps, year range, ISBN shape (`src/api.c:validate_book`)
3. [info] Single-threaded, one-connection-per-accept, localhost-only server (`src/http.c`)
4. [info] ISBN checksum not verified — shape-only (`src/api.c:valid_isbn`)

No requirement gaps, no build/test failures, no skipped or disabled tests.

## Reproduce

```bash
cd "experiments/adrianco/experiment-86-haiku55-alllang/rest-api-crud/runs/effort=low_language=c_model=claude-haiku-5-5_prompt=neutral/rep2"
cat scores.json                       # stored mechanical scores (build+test not re-run)
cat ../../../REQUIREMENTS.json        # pinned 12-requirement checklist
grep -c 'CHECK(' tests/test_all.c     # 89 effective assertions
grep -rnE 't\.Skip|@skip|#\[ignore\]' src tests   # no test skips (skip_ws is JSON whitespace)
# To build/test locally (not required for scoring):
make && make test
```
