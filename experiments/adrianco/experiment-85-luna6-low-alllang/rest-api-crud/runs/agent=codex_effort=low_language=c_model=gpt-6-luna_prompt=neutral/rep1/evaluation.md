# Evaluation: rest-api-crud · agent=codex effort=low language=c model=gpt-6-luna prompt=neutral · rep 1

## Summary

- **Factors:** language=c, model=gpt-6-luna, agent=codex, effort=low, prompt=neutral, framework=unknown
- **Task type:** REPAIR (prior attempt's bug: `GET /books/{id}` always returned 404 — see FEEDBACK.md)
- **Status:** ok — build + all tests pass (`test_coverage=1.0` from scores.json)
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 4 passed / 0 failed / 0 skipped (4 effective)
- **Build:** pass (not re-run — `test_coverage=1.0`, `defect_rate=1.0` from scores.json)
- **Lint:** pass — `code_quality=0.9556` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 1 medium, 1 low)

The repair succeeded. The prior 404 bug on `GET /books/{id}` is fixed at `book_service.c:34`: the handler now steps the statement, checks `found`, `sqlite3_reset`s, and serializes the row (404 only when no row). Stored scores confirm the build and all tests pass.

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book | ✓ implemented | `book_service.c:31-33` — parses title/author/year/isbn, INSERT, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `book_service.c:30` — SELECT ... ORDER BY id, JSON array |
| R3 | GET /books ?author= filter | ✓ implemented | `book_service.c:30` — `WHERE author=?` bound from query arg |
| R4 | GET /books/{id} single book | ✓ implemented | `book_service.c:34` — bound id, 200 with row / 404 if absent (repaired) |
| R5 | PUT /books/{id} update | ✓ implemented | `book_service.c:36` — merges supplied fields over existing row, UPDATE |
| R6 | DELETE /books/{id} | ✓ implemented | `book_service.c:35` — DELETE, 200 if changed else 404 |
| R7 | SQLite / embedded DB | ✓ implemented | `book_service.c:3,42` — sqlite3, `BOOKS_DB` file, `CREATE TABLE books` |
| R8 | JSON responses + status codes | ✓ implemented | `respond`/`error` set `application/json`; 201/200/400/404/413 used |
| R9 | Validation: title+author required | ✓ implemented | `book_service.c:32` — missing/empty title or author → 400 |
| R10 | GET /health | ✓ implemented | `book_service.c:29` — returns `{"status":"ok"}` 200 |
| R11 | README.md setup/run | ✓ implemented | `README.md` — deps, `make`, run, `BOOKS_DB`, API, tests |
| R12 | ≥3 unit/integration tests | ✓ implemented | `test_api.c` — 4 tests run and pass (`test_coverage=1.0`) |

Note: the tests validate static helpers, not the HTTP handler — the repaired route is fixed by inspection, not covered by a regression test (see findings).

## Build & Test

Not re-run per skill Step 2 — stored scores used as the build+test signal:

```text
scores.json: test_coverage=1.0  defect_rate=1.0  maintainability=1.0
             code_quality=0.9556  idiomatic=0.12  token_efficiency=0.0118
=> build succeeded and all 4 C tests passed ("4 tests passed").
```

Test command (for reference, not executed here): `make test` →
compiles `test_api.c` (which `#define UNIT_TEST`s and `#include`s `book_service.c`), runs `./test_book_service`.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 110 (book_service.c 43 dense lines, test_api.c 67) |
| Files | 14 (incl. logs, binary, summary/) |
| Dependencies | sqlite3, libmicrohttpd (system, via pkg-config) |
| Tests total | 4 |
| Tests effective | 4 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run) |

## Findings

Top findings (full list in `findings.jsonl`):

1. [medium] Tests never drive the HTTP handler; the repaired `GET /books/{id}` route is unverified by any test (`test_api.c:60-66`).
2. [low] PUT success path leaks the merged field strings (`book_service.c:36`).

No critical or high findings — the run is a clean pass.

## Reproduce

```bash
cd "experiments/adrianco/experiment-85-luna6-low-alllang/rest-api-crud/runs/agent=codex_effort=low_language=c_model=gpt-6-luna_prompt=neutral/rep1"
cat scores.json            # stored build/test/quality scores (not re-run)
make test                  # build + run the 4 C unit tests (requires sqlite3, libmicrohttpd)
```
