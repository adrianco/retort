# Evaluation: language=erlang_model=claude-opus-4-8 · rep 2

## Summary

- **Factors:** language=erlang, model=claude-opus-4-8, agent=unknown, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective)
- **Build:** pass — rebar3 compile + eunit completed successfully
- **Lint:** unavailable — no Erlang linter configured in rebar.config
- **Architecture:** summary skill unavailable
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/booklib_router.erl:24` POST handler → `booklib_db:create/1`; `booklib_db.erl:66` validates & stores in dets with auto-increment ID. Tests: `create_and_get/0`, `create_flow/1` |
| R2 | GET /books lists all books | ✓ implemented | `src/booklib_router.erl:19` GET /books → `booklib_db:list/1`; returns `{books, count}`. Test: `create_flow/1:131` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/booklib_router.erl:20` extracts `author` query param; `booklib_db.erl:143-148` `filter_by_author/2` with case-insensitive match. Test: `author_filter/0` |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `src/booklib_router.erl:35` GET /books/:id → `booklib_db:get/1`, 404 if not found. Tests: `create_flow/1`, `missing_book/1` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/booklib_router.erl:43` PUT handler with validation and 404 handling. Tests: `update_book/0`, `put_delete/1` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/booklib_router.erl:54` DELETE handler. Tests: `delete_book/0`, `put_delete/1` |
| R7 | Data stored in SQLite (or embedded DB equivalent) | ✓ implemented | `src/booklib_db.erl:58` uses `dets` (Erlang's built-in disk-based embedded DB), file configured via `db_file` app env. README.md documents the choice. |
| R8 | Returns JSON responses with appropriate HTTP status codes | ✓ implemented | `src/booklib_http.erl:140-149` sends JSON with Content-Type: application/json; status codes 200/201/400/404/405/422/500 used correctly. All HTTP tests verify codes. |
| R9 | Input validation: title and author are required | ✓ implemented | `src/booklib_db.erl:154-169` `validate/1` with `required_string/2` for title and author; returns 422 with error details. Tests: `validation_required/0`, `invalid_create/1` |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/booklib_router.erl:15` returns `{"status":"ok"}` with 200. Test: `health/1` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 146 lines covering build, run, test, API docs, and examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | 10 tests: 5 DB/validation (create_and_get, validation_required, author_filter, update_book, delete_book) + 5 HTTP end-to-end (health, create_flow, invalid_create, missing_book, put_delete) |

## Build & Test

```text
$ rebar3 eunit
===> Verifying dependencies...
===> Analyzing applications...
===> Compiling booklib
===> Performing EUnit tests...

  booklib_tests: create_and_get (create then get a book)...[0.003 s] ok
  booklib_tests: validation_required (validation rejects missing fields)...ok
  booklib_tests: author_filter (author filter narrows the list)...[0.010 s] ok
  booklib_tests: update_book (update replaces fields)...[0.002 s] ok
  booklib_tests: delete_book (delete removes a book)...[0.001 s] ok
  booklib_tests: health check...[0.078 s] ok
  booklib_tests: POST creates and GET retrieves...[0.001 s] ok
  booklib_tests: POST with missing title is rejected...ok
  booklib_tests: GET unknown id is 404...ok
  booklib_tests: PUT and DELETE lifecycle...[0.004 s] ok

  All 10 tests passed.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 640 (.erl + .app.src, excl. tests) |
| Lines of test code | 184 |
| Total lines | 824 |
| Files | 15 (excluding _build/ and .git/) |
| Dependencies | 0 (OTP-only, no external deps) |
| Tests total | 10 |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build duration | <1s (compile) |

## Findings

Top 5 by severity (full list in `findings.jsonl`):

1. [info] 405 Method Not Allowed responses on known routes — beyond spec
2. [info] Request body size limiting (1 MiB cap) — beyond spec
3. [info] URL percent-decoding on query parameters — beyond spec

## Reproduce

```bash
cd experiment-8/runs/language=erlang_model=claude-opus-4-8/rep2
rebar3 eunit
find . -name "*.erl" -o -name "*.app.src" | grep -v _build | xargs wc -l
find . -type f -not -path "*/_build/*" -not -path "*/.git/*" | wc -l
```
