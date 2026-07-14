# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.go | HTTP server, SQLite init, and all route handlers | `main()`, `initDB()`, `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`, `healthCheck` |
| app_test.go | httptest-based handler tests | 13 test functions |
| go.mod / go.sum | Go module dependencies (Gin + go-sqlite3) | module `book-api` |
| README.md | Setup, run, and API-usage instructions | — |
