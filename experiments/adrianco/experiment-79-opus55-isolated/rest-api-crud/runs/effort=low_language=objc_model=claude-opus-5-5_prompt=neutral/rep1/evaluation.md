# Evaluation: rest-api-crud · effort=low_language=objc_model=claude-opus-5-5_prompt=neutral · rep 1

## Summary

- **Factors:** language=objc, model=claude-opus-5-5, prompt=neutral, effort=low
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing (pinned `REQUIREMENTS.json`)
- **Tests:** 10 passed / 0 failed / 0 skipped (10 effective; 79 checks)
- **Build:** pass — clean compile, no warnings (`code_quality=1.0` from scores.json)
- **Lint:** pass — `code_quality=1.0` from scores.json
- **Architecture:** see `summary/index.md`
- **Findings:** 3 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 3 info)

Evidence: `scores.json` reports `test_coverage=1.0`, `code_quality=1.0`, `defect_rate=1.0`
(build + all tests passed). The agent's own `_agent_stdout.log` shows `make test` →
"79 checks, 0 failures, 10/10 tests passed" with a warning-clean `clang` compile.

## Requirements

Pinned checklist from `rest-api-crud/REQUIREMENTS.json` (constant denominator = 12).

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books creates a book (title, author, year, isbn) | ✓ implemented | `src/BookAPI.m` POST `/books` → `BookStore.createBook:`; `tests/BookTests.m:TestCreateAndGet` (201 + Location) |
| R2 | GET /books lists all books | ✓ implemented | `src/BookAPI.m` GET `/books` → `listBooksWithAuthor:nil`; `TestListAndAuthorFilter` (count 3) |
| R3 | GET /books supports ?author= filter | ✓ implemented | `BookStore.m` `WHERE author = ? COLLATE NOCASE`; `TestListAndAuthorFilter` (exact + case-insensitive) |
| R4 | GET /books/{id} returns one book (404 if absent) | ✓ implemented | `src/BookAPI.m` `/books/` branch → `bookWithID:`; `TestNotFoundAndMethodNotAllowed` (404 on /books/42) |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/BookAPI.m` PUT → `updateBook:fields:`; `TestUpdate` (200 + 404 on /books/99) |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/BookAPI.m` DELETE → `deleteBook:found:`; `TestDelete` (204 then 404) |
| R7 | Data stored in SQLite | ✓ implemented | `src/BookStore.m` `sqlite3_open` + `books` table; `TestPersistenceAcrossReopen` (survives close/reopen) |
| R8 | JSON responses with appropriate status codes | ✓ implemented | `BookAPI.m` `JSONResponse` (201/200/204/400/404/405); `Content-Type: application/json` asserted in `TestEndToEndOverHTTP` |
| R9 | Validation: title and author required | ✓ implemented | `BookAPI.m` `fieldsFromBody:failure:` (required, non-blank, string-typed); `TestValidation` (multiple 400s) |
| R10 | GET /health health check | ✓ implemented | `src/BookAPI.m` `/health` → `{"status":"ok"}`; `TestHealth` |
| R11 | README.md with setup/run instructions | ✓ implemented | `README.md` — build/run/test, env vars, API table, examples |
| R12 | At least 3 unit/integration tests | ✓ implemented | `tests/BookTests.m` — 10 test functions, 79 checks; `test_coverage=1.0` |

No partial, missing, or cannot-verify requirements.

## Build & Test

Scores read from `scores.json` (not re-run, per skill guidance):

```text
{"code_quality": 1.0, "test_coverage": 1.0, "defect_rate": 1.0,
 "maintainability": 0.807, "idiomatic": 0.82, "token_efficiency": 0.085}
```

Agent's recorded run (`_agent_stdout.log`):

```text
cc -O2 -Wall -Wextra -Wno-unused-parameter -fobjc-arc -Isrc \
  src/BookStore.m src/BookAPI.m src/HTTPServer.m tests/BookTests.m \
  -o build/books-tests -framework Foundation -lsqlite3
./build/books-tests
PASS health / create and get / optional fields default to null / validation /
     list and author filter / update / delete / not found+method not allowed /
     persistence across reopen / end-to-end over HTTP
79 checks, 0 failures, 10/10 tests passed
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only, src/) | 652 |
| Lines of code (tests) | 279 |
| Files (src + tests) | 8 |
| Dependencies (third-party) | 0 (Foundation + system libsqlite3 only) |
| Tests total | 10 (79 checks) |
| Tests effective | 10 |
| Skip ratio | 0% |
| Build | pass (clean) |

## Findings

All 3 findings are `info` (no defects). Full list in `findings.jsonl`:

1. [info] End-to-end HTTP test over a real socket, beyond the 3-test minimum
2. [info] SQL-injection safety is explicitly tested (bound params)
3. [info] HTTP server is single-request-per-connection (documented limitation)

## Reproduce

```bash
cd /Users/adriancockcroft/code/retort/experiments/adrianco/experiment-79-opus55-isolated/rest-api-crud/runs/effort=low_language=objc_model=claude-opus-5-5_prompt=neutral/rep1
cat scores.json                       # stored mechanical scores (build/test/lint)
grep -rniE "skip|disabled|XCTSkip" tests/   # 0 skips
make test                             # optional re-run: 10/10 tests, 79 checks
```
