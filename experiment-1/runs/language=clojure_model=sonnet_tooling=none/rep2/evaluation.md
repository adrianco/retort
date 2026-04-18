# Evaluation: language=clojure_model=sonnet_tooling=none · rep 2

## Summary

- **Factors:** language=clojure, model=sonnet, tooling=none
- **Status:** ok
- **Requirements:** 9/9 implemented, 0 partial, 0 missing
- **Tests:** 13 passed / 0 failed / 0 skipped (13 effective)
- **Build:** pass — Clojure CLI successfully compiled and ran tests
- **Lint:** unavailable — clj-kondo not available in environment
- **Architecture:** REST API with Ring/Compojure routing, SQLite persistence, layered structure (core/handlers/db)
- **Findings:** 5 items in `findings.jsonl` (0 critical, 0 high, 0 medium, 0 low, 5 info)

## Requirements

| ID | Requirement (short) | Status | Evidence |
|----|----|----|----|
| R1 | POST /books endpoint with validation | ✓ implemented | src/book_api/handlers.clj:20-25, test/book_api/core_test.clj:52-72 |
| R2 | GET /books with optional ?author= filter | ✓ implemented | src/book_api/handlers.clj:27-29, test/book_api/core_test.clj:91-98 |
| R3 | GET /books/{id} endpoint | ✓ implemented | src/book_api/handlers.clj:31-36, test/book_api/core_test.clj:104-113 |
| R4 | PUT /books/{id} update endpoint | ✓ implemented | src/book_api/handlers.clj:38-48, test/book_api/core_test.clj:119-129 |
| R5 | DELETE /books/{id} endpoint | ✓ implemented | src/book_api/handlers.clj:50-56, test/book_api/core_test.clj:135-144 |
| R6 | SQLite persistence | ✓ implemented | src/book_api/db.clj:1-60 uses next.jdbc with sqlite-jdbc |
| R7 | JSON responses with proper HTTP status codes | ✓ implemented | src/book_api/handlers.clj:5-9 (201, 200, 400, 404, 204 used appropriately) |
| R8 | Input validation (title, author required) | ✓ implemented | src/book_api/handlers.clj:11-15 validates both fields |
| R9 | Health check endpoint GET /health | ✓ implemented | src/book_api/core.clj:12, test/book_api/core_test.clj:43-46 |

## Build & Test

```
clojure -M:test

Testing book-api.core
Testing book-api.core-test
WARNING: A restricted method in java.lang.System has been called
[... sqlite-jdbc native library warnings omitted ...]

Testing book-api.db
Testing book-api.handlers

Ran 13 tests containing 28 assertions.
0 failures, 0 errors.
```

## Metrics

| Metric | Value |
|--------|-------|
| Lines of code (source only) | 144 |
| Files | 9 |
| Dependencies | 7 |
| Tests total | 13 |
| Tests effective | 13 |
| Skip ratio | 0% |
| Build status | pass |

## Findings

Top items by severity (full list in `findings.jsonl`):

1. [info] All required endpoints implemented (src/book_api/core.clj:11-18)
2. [info] Comprehensive test coverage with 13 tests (test/book_api/core_test.clj)
3. [info] Input validation working correctly (src/book_api/handlers.clj:11-15)
4. [info] Author filter with partial matching implemented (src/book_api/db.clj:33-42)
5. [info] HTTP status codes are appropriate (201, 200, 400, 404, 204)

## Deliverables Checklist

- ✓ Working source code in workspace (src/book_api/{core,handlers,db}.clj)
- ✓ README.md with setup and run instructions (includes API reference)
- ✓ Tests — 13 passing unit/integration tests (exceeds minimum of 3)

## Reproduce

```bash
cd experiment-1/runs/language=clojure_model=sonnet_tooling=none/rep2

# Run tests
clojure -M:test

# Start server on port 3000
clojure -M:run

# Or start on custom port
PORT=8080 clojure -M:run

# Example API call (with server running)
curl -X POST http://localhost:3000/books \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","author":"Author","year":2026,"isbn":"123"}'
```
