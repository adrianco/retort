# Evaluation: effort=low language=c model=claude-opus-5-5 prompt=neutral · rep 2

## Summary

- **Factors:** language=c, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 19 assertions passed / 0 failed / 0 skipped (19 effective) — plus a curl end-to-end script
- **Build:** pass (test_coverage=1.0 from scores.json ⇒ build + tests succeeded)
- **Lint:** pass (code_quality=1.0 from scores.json)
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 1 low, 2 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/books.c:272 write_book`, INSERT at `:279`, routed at `:323`, returns 201 |
| R2 | GET /books lists all books | ✓ implemented | `src/books.c:249 list_books`, routed at `:322` |
| R3 | GET /books supports ?author= filter | ✓ implemented | `src/books.c:250` query_param + `WHERE author=?` at `:253` |
| R4 | GET /books/{id} returns single book (404 if absent) | ✓ implemented | `src/books.c:201 get_one` (404 at `:210`), routed `:329` |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/books.c:281` UPDATE, 404 on no-change `:290`, routed `:330` |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/books.c:294 delete_book`, 204/404, routed `:331` |
| R7 | Data stored in SQLite | ✓ implemented | `src/books.c:178 books_open` sqlite3, CREATE TABLE `:181` |
| R8 | JSON responses + appropriate HTTP status codes | ✓ implemented | `src/server.c:27 reply` sets Content-Type json; 201/200/204/400/404/405 throughout |
| R9 | Validation: title and author required | ✓ implemented | `src/books.c:169 validate` rejects blank/bad title & author → 400 |
| R10 | GET /health health check | ✓ implemented | `src/books.c:317` returns 200 `{"status":"ok"}` |
| R11 | README with setup & run instructions | ✓ implemented | `README.md` — build/run/test/endpoints documented |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/test_books.c` 5 functions, 19 assertions + `tests/http_test.sh`; test_coverage=1.0 |

No requirements are partial or missing. No skipped or disabled tests were found.

## Build & Test

Scores were read from `scores.json` (inline gate output); the toolchain was **not** re-run.

```text
scores.json
{"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
 "maintainability": 0.5419888788743518, "idiomatic": 0.62,
 "token_efficiency": 0.02615382428610009}
```

`test_coverage=1.0` and `defect_rate=1.0` ⇒ `make test` built `test_books` +
`books_server` and both the C unit/integration suite and the curl end-to-end
script passed. Test binary asserts 19 CHECK conditions across health, full CRUD,
list+filter, validation (8 bad bodies), and JSON-escaping/routing edge cases.

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 568 (books.c 335, server.c 83, books.h 14, test_books.c 96, http_test.sh 20, Makefile 20) |
| Files (excl. build artifacts) | 14 |
| Dependencies | 1 external lib (libsqlite3); no package manifest |
| Tests total | 19 assertions (5 functions) + 1 e2e script |
| Tests effective | 19 |
| Skip ratio | 0% |
| Build duration | n/a (not re-run; scores from inline gate) |

## Findings

Top findings by severity (full list in `findings.jsonl`) — all informational, none are deductions:

1. [low] N3 — Flat JSON parser rejects nested objects/arrays (`src/books.c:119`); sufficient for the flat book schema.
2. [info] N1 — Single-threaded sequential server, one connection at a time (`src/server.c:77`); documented in README.
3. [info] N2 — PUT replaces the whole record (`src/books.c:281`); documented full-replace semantics.

## Reproduce

```bash
cd experiments/adrianco/experiment-75-opus55-alllang/rest-api-crud/runs/effort=low_language=c_model=claude-opus-5-5_prompt=neutral/rep2
cat scores.json                         # build/test/lint scores (do not re-run)
cat ../../../REQUIREMENTS.json          # pinned 12-item checklist
grep -cE 'CHECK\(' tests/test_books.c   # 19 assertions
# optional full rebuild: make test      # builds + runs C suite + curl e2e
```
