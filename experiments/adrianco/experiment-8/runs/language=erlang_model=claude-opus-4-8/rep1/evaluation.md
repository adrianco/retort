# Evaluation: language=erlang_model=claude-opus-4-8 · rep 1

## Summary

- **Factors:** language=erlang, model=claude-opus-4-8, agent=unknown, framework=unknown
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 12 passed / 0 failed / 0 skipped (12 effective)
- **Build:** pass (derived from rebar3 eunit) — compiled clean with 2 deprecation warnings
- **Lint:** pass — code_quality=1.0 from retort.db; 2 low-severity deprecation warnings in test files
- **Architecture:** summary skill unavailable
- **Findings:** 2 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 2 low)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|---------------------|--------|----------|
| R1 | POST /books creates a new book (title, author, year, isbn) | ✓ implemented | `src/books_handler.erl:33` POST handler → `src/book_store.erl:42` create/1; `build_book/2` at :177 stores all four fields |
| R2 | GET /books lists all books | ✓ implemented | `src/books_handler.erl:25` GET handler → `src/book_store.erl:47` list/0 returns all books |
| R3 | GET /books supports an ?author= filter | ✓ implemented | `src/books_handler.erl:27` parses `<<"author">>` from query string → `src/book_store.erl:52` list/1 filters by exact author match |
| R4 | GET /books/{id} returns a single book by id | ✓ implemented | `src/books_handler.erl:48` GET with id binding → `src/book_store.erl:57` get/1; returns 404 if absent |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/books_handler.erl:56` PUT handler → `src/book_store.erl:62` update/2 merges attrs onto existing book |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/books_handler.erl:70` DELETE handler → `src/book_store.erl:67` delete/1; returns 404 if absent |
| R7 | Data stored in SQLite (or embedded DB equivalent) | ✓ implemented | Uses `dets` (Erlang/OTP built-in disk-based term storage); `src/book_store.erl:80` opens file; `books.dets` present in workspace |
| R8 | Returns JSON responses with appropriate HTTP status codes | ✓ implemented | `src/books_handler.erl` uses 200/201/204/400/404/405; `src/health_handler.erl` returns 200; JSON via `json:encode`; content-type header set at :106 |
| R9 | Input validation: title and author are required | ✓ implemented | `src/book_store.erl:207` validate/1 checks both fields; `present/1` at :214 rejects undefined/null/empty/whitespace; tested in `test/book_store_tests.erl:50` and `test/booksapp_http_tests.erl:57` |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/health_handler.erl:8` returns `{"status":"ok"}` with 200; route at `src/booksapp_app.erl:13`; tested in `test/booksapp_http_tests.erl:40` |
| R11 | README.md with setup and run instructions | ✓ implemented | `README.md` — 104 lines covering setup, run instructions, API table, curl examples, test command, project layout |
| R12 | At least 3 unit/integration tests | ✓ implemented | 6 unit tests in `test/book_store_tests.erl` + 6 integration tests in `test/booksapp_http_tests.erl` = 12 total; all pass |

## Build & Test

Scores from retort.db: test_coverage=1.0, code_quality=1.0, defect_rate=0.0, idiomatic=0.92.

Fallback verification (toolchain available, DB inaccessible via -readonly):

```text
rebar3 eunit
===> Compiling booksapp
  Warning: test/book_store_tests.erl:11 — 'catch ...' is deprecated
  Warning: test/book_store_tests.erl:17 — 'catch ...' is deprecated
===> Performing EUnit tests...
  book_store_tests: create_and_get...ok
  book_store_tests: create_requires_title_and_author...ok
  book_store_tests: list_and_filter_by_author...ok
  book_store_tests: update_book...ok
  book_store_tests: update_missing_returns_not_found...ok
  book_store_tests: delete_book...ok
  booksapp_http_tests: health_endpoint...ok
  booksapp_http_tests: create_and_fetch_book...ok
  booksapp_http_tests: create_validation_error...ok
  booksapp_http_tests: list_with_author_filter...ok
  booksapp_http_tests: update_and_delete...ok
  booksapp_http_tests: missing_book_is_404...ok
  All 12 tests passed.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 402 |
| Lines of code (tests) | 220 |
| Lines of code (total .erl) | 622 |
| Files | 16 |
| Dependencies | 1 (cowboy 2.12.0) |
| Tests total | 12 |
| Tests effective | 12 |
| Skip ratio | 0% |
| Build duration | <1s (compiled clean) |

## Findings

Top 2 by severity (full list in `findings.jsonl`):

1. [low] Deprecated 'catch' syntax in test setup — `test/book_store_tests.erl:11`
2. [low] Deprecated 'catch' syntax in test cleanup — `test/book_store_tests.erl:17`

## Reproduce

```bash
cd experiment-8/runs/language=erlang_model=claude-opus-4-8/rep1
cat stack.json
cat TASK.md
# Scores were read from retort.db (experiment-8/retort.db)
# Fallback: copy workspace to temp dir and run:
rebar3 eunit
# Check for skipped tests:
grep -rE "skip|Skip" test/ --include="*.erl"
# Lines of code:
find . -name "*.erl" -not -path "*/_build/*" | xargs wc -l
```
