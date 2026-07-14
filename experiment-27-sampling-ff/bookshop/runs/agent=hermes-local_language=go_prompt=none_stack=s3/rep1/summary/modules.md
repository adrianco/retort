# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.go | HTTP server, SQLite init, all route handlers | `main`, `initDB`, `healthHandler`, `createBookHandler`, `listBooksHandler`, `getBookHandler`, `updateBookHandler`, `deleteBookHandler` |
| app_test.go | Gin/httptest integration tests against an in-memory SQLite DB | 6 test functions + `setupTestDB`, `newTestRouter`, `TestMain` |
| go.mod / go.sum | Module definition and dependency checksums (gin, go-sqlite3) | — |
| README.md | Setup, run, and API usage documentation | — |
