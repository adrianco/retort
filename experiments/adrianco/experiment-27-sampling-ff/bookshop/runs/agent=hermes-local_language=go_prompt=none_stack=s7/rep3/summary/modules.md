# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.go | Gin HTTP server, SQLite-backed book CRUD handlers, and `main()` bootstrap | `Book`, `CreateBookRequest`, `Database`, `NewDatabase()`, `(*Database).Close`, `HealthCheck`, `(*Database).CreateBook`, `(*Database).ListBooks`, `(*Database).GetBook`, `(*Database).UpdateBook`, `(*Database).DeleteBook`, `main()` |
| app_test.go | Integration tests for all routes plus a full-CRUD flow, using httptest recorders | 16 `Test*` functions, `TestMain`, `setupTestDB()`, `teardownTestDB()`, `setupTestRouter()` |
| go.mod / go.sum | Module definition (`bookapi`, Go 1.21) and dependency checksums | gin-gonic/gin, mattn/go-sqlite3 |

Non-source artifacts present but not summarized: `bookapi` (compiled binary), `books.db`/`test_books.db` (runtime SQLite files if present), `README.md`, and harness metadata files (`_meta.json`, `scores.json`, `stack.json`, `.hermes_usage.json`, `.idiomatic_cache.json`, `_agent_stdout.log`, `_agent_stderr.log`).
