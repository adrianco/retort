# Architecture Summary: Book API (Clojure)

## Overview

This run implements a REST API service for managing a book collection in Clojure using Ring (HTTP abstraction), Reitit (routing), and SQLite (persistence). The codebase consists of three main modules: HTTP server setup and routing (core.clj), request handlers with validation (handlers.clj), and database abstraction (db.clj). A comprehensive test suite validates functionality, though integration tests currently fail due to response serialization issues with muuntaja middleware.

## Structure

**See detailed documentation:**
- [Modules](modules.md) — Source files, purposes, and entry points
- [Interfaces](interfaces.md) — HTTP API endpoints, data schema, and configuration
- [Control Flow](flow.md) — Request-response sequences and architectural narrative

## Key Components

### 1. HTTP Layer (Ring + Reitit)
- `core.clj` defines all routes and starts Jetty server on port 3000
- Routes map to handlers in `handlers.clj`
- muuntaja middleware should handle JSON serialization (currently has a bug)

### 2. Request Handlers (handlers.clj)
- 6 REST endpoints: CREATE, READ, LIST, UPDATE, DELETE, HEALTH
- Input validation for title and author on create
- Proper HTTP status codes: 201 (created), 200 (ok), 204 (deleted), 404 (not found), 422 (validation error)

### 3. Database Layer (db.clj)
- Uses next.jdbc for database abstraction
- SQLite file-based storage (`books.db`)
- CRUD functions with parameterized queries to prevent SQL injection
- Table auto-initialization on startup

## Dependencies

11 dependencies including:
- Ring 1.11.0 (HTTP framework)
- Reitit 0.7.0 (routing with interceptor middleware)
- muuntaja 0.6.10 (content negotiation)
- next.jdbc 1.3.894 (database abstraction)
- sqlite-jdbc 3.45.1.0 (SQLite driver)
- clojure.data.json 2.4.0 (JSON serialization fallback)

## Test Coverage

8 integration tests in `core_test.clj`:
- Health check: 1 test
- Create with validation: 3 tests
- Create and retrieve: 1 test
- List and filter: 2 tests
- Update: 2 tests
- Delete: 2 tests
- Get nonexistent: 1 test

**Current status:** 4 pass, 4 fail (50% pass rate)

## Known Issues

1. **Response Serialization Bug** — POST /books handler returns a map, but muuntaja middleware is not properly converting it to JSON before returning to client. Tests fail when trying to parse response body as JSON.

2. **Missing README.md** — No setup/run documentation provided.

3. **Cascading Test Failures** — Because POST response bodies are not properly serialized, downstream tests (PUT, DELETE) cannot extract book IDs and operate on non-existent resources (404 errors).

## Metrics

| Metric | Value |
|--------|-------|
| Source files | 3 |
| Test files | 1 |
| Lines of source code | 157 |
| Lines of test code | 143 |
| Total dependencies | 11 |
| Tests written | 8 |
| Tests passing | 4 |
| Tests failing | 4 |
| Failure rate | 50% |

## Reproduction

```bash
cd experiment-1/runs/language=clojure_model=sonnet_tooling=beads/rep3-failed

# Prepare environment
clojure -P -M:test

# Run tests
clojure -M:test

# Start server (manual testing)
clojure -M:run
```

See `evaluation.md` for detailed requirements assessment and findings.
