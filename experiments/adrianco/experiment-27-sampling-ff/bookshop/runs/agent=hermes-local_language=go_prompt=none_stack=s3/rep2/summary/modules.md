# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.go | HTTP server, SQLite init, all route handlers | `main`, `initDB`, `healthHandler`, `createBookHandler`, `listBooksHandler`, `getBookHandler`, `updateBookHandler`, `deleteBookHandler` |
| app_test.go | httptest-based API tests over an in-memory SQLite DB | 12 test functions, `setupTestDB`, `newTestRouter` |
| go.mod / go.sum | Module + pinned deps (Gin, go-sqlite3) | module `bookapi` |
| README.md | Setup, run, API docs, curl examples | — |
