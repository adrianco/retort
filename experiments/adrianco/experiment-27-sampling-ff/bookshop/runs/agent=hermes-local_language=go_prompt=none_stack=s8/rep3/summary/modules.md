# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.go | Gin HTTP server, SQLite-backed book CRUD handlers | `main`, `initDB`, `validateBook`, `healthCheck`, `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`, `Book`, `CreateBookRequest`, `UpdateBookRequest` |
| app_test.go | httptest-based integration tests for all routes | `TestMain` + 23 `Test*` functions |

Non-source files present but excluded: `README.md`, `TASK.md`, `go.mod`, `go.sum`, `stack.json`, `scores.json`, `_meta.json`, `_agent_stdout.log`, `_agent_stderr.log`, `.hermes_usage.json`, `.idiomatic_cache.json`.
