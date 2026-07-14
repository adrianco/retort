# Evaluation: language=clojure_model=sonnet_tooling=none · rep 2

## Summary

- **Factors:** language=clojure, model=sonnet, tooling=none
- **Status:** ok
- **Requirements:** 12/12 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass (derived from test run) — deps resolved + compiled cleanly
- **Lint:** unavailable — no Clojure linter configured
- **Architecture:** see `summary/` (modules.md, interfaces.md, flow.md)
- **Findings:** 1 item in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 1 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----------------------|--------|----------|
| R1 | POST /books creates a new book | ✓ implemented | `src/book_api/handlers.clj:20-25` create-book-handler; `src/book_api/db.clj:24-31` create-book!; test: test-create-book-success |
| R2 | GET /books lists all books | ✓ implemented | `src/book_api/handlers.clj:27-29` list-books-handler; `src/book_api/db.clj:33-42` get-books; tests: test-list-books-empty, test-list-books-returns-all |
| R3 | GET /books ?author= filter | ✓ implemented | `src/book_api/handlers.clj:28` extracts author query-param; `src/book_api/db.clj:37-39` WHERE author LIKE filter; test: test-list-books-author-filter |
| R4 | GET /books/{id} returns single book | ✓ implemented | `src/book_api/handlers.clj:31-36` get-book-handler with 404; tests: test-get-book-found, test-get-book-not-found |
| R5 | PUT /books/{id} updates a book | ✓ implemented | `src/book_api/handlers.clj:38-48` update-book-handler with validation + 404; tests: test-update-book-success, test-update-book-not-found |
| R6 | DELETE /books/{id} deletes a book | ✓ implemented | `src/book_api/handlers.clj:50-56` delete-book-handler returns 204/404; tests: test-delete-book-success, test-delete-book-not-found |
| R7 | Data stored in SQLite | ✓ implemented | `src/book_api/db.clj:5` db-spec {:dbtype "sqlite" :dbname "books.db"}; uses next.jdbc + sqlite-jdbc |
| R8 | JSON responses with appropriate HTTP status codes | ✓ implemented | `src/book_api/handlers.clj:6-9` json-response sets Content-Type application/json via cheshire; correct codes: 200, 201, 204, 400, 404 |
| R9 | Input validation: title and author required | ✓ implemented | `src/book_api/handlers.clj:11-15` validate-book checks empty title/author; tests: test-create-book-missing-title, test-create-book-missing-author |
| R10 | GET /health health-check endpoint | ✓ implemented | `src/book_api/core.clj:12` route; `src/book_api/handlers.clj:17-18` returns {:status "ok"}; test: test-health-check |
| R11 | README.md with setup and run instructions | ✓ implemented | README.md: prerequisites, setup, running server (clojure -M:run), running tests (clojure -M:test), full API reference |
| R12 | At least 3 unit/integration tests | ✓ implemented | 13 deftest definitions in test/book_api/core_test.clj, all passing (28 assertions) |

## Build & Test

```text
clojure -M:test
(dependencies downloaded and compiled successfully)
```

```text
Testing book-api.core-test

Ran 13 tests containing 28 assertions.
0 failures, 0 errors.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 144 |
| Lines of code (incl. tests) | 295 |
| Files | 7 |
| Dependencies | 8 (prod) + 1 (test) |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build duration | N/A (derived from test run) |

## Findings

Top findings by severity (full list in `findings.jsonl`):

1. [info] No Clojure linter executed — no clj-kondo or eastwood configured

## Reproduce

```bash
cd experiment-1/runs/language=clojure_model=sonnet_tooling=none/rep2
clojure -M:test
find src test -name "*.clj" | xargs wc -l
```
