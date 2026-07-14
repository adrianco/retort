# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| app.go | Gin HTTP server, SQLite init, route handlers | `main`, `initDB`, `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`, `healthCheck` |
| app_test.go | httptest-based integration tests for all routes | 7 test functions (`TestHealthCheck`, `TestCreateBook`, `TestListBooks`, `TestGetBook`, `TestUpdateBook`, `TestDeleteBook`, `TestEmptyList`) |

Helpers in `app.go`: `validateBook` (required-field check), `scanBook` (defined but never called — dead code).
