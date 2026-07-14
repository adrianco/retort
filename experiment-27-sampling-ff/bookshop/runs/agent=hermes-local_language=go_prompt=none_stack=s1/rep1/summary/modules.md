# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.go | HTTP server, Gin routes, SQLite handlers | `main()`, `initDB()`, `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`, `healthCheck`, `Book` |
| app_test.go | HTTP integration tests via httptest | 11 test functions, `setupTestDB()`, `setupTestRouter()`, `teardownTestDB()` |
