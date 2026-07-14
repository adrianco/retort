# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite store, route handlers, validation | `Book`, `BookStore`, `NewBookStore()`, `(*BookStore).ServeHTTP`, `main()` |
| main_test.go | httptest-based API + store tests | 12 test functions (14 cases incl. subtests) |

Skipped: `book-api` (compiled binary), `go.mod`, `go.sum` (build metadata), `.hermes_usage.json`, `.idiomatic_cache.json`, `_meta.json`, logs.
