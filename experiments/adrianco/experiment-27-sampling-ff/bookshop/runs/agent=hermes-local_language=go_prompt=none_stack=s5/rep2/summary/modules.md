# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.go | HTTP server, Gin route handlers, SQLite persistence | `main()`, `initDB()`, `healthCheck`, `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook` |
| app_test.go | HTTP integration tests via httptest | 10 test functions, `setupTestDB()`, `cleanupTestDB()` |
| go.mod / go.sum | Module definition + dependency lock | `gin-gonic/gin v1.9.1`, `mattn/go-sqlite3 v1.14.22` |
| README.md | Setup/run/test documentation | — |
