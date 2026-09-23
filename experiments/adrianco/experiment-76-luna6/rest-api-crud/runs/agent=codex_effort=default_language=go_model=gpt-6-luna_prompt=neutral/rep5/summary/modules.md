# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry, SQLite open + schema bootstrap, HTTP server | `main()`, `openDatabase()`, `errNotFound` |
| handler.go | HTTP routing and request/response handling | `newHandler()`, `apiHandler`, `writeJSON()` |
| books.go | Book model and SQLite-backed store (CRUD + filter + validation) | `Book`, `bookStore`, `validateBook()` |
| handler_test.go | HTTP integration tests via `httptest` | 3 test functions |
