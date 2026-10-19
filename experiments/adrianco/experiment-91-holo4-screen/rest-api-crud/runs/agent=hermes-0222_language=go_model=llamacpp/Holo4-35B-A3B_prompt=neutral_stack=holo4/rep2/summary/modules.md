# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Wires DB + routes, starts HTTP server with graceful shutdown | `main`, mux on `/health`, `/books`, `/books/` |
| handler.go | All HTTP handlers, routing-by-method, validation, JSON helpers | `booksHandler`, `booksByIDHandler`, `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`, `healthHandler` |
| db.go | SQLite connection + schema migration | `initDB()` |
| book.go | Domain structs and request/response DTOs | `Book`, `CreateBookRequest`, `UpdateBookRequest`, `ErrorResponse` |
| handler_test.go | HTTP handler integration tests against a temp SQLite DB | 8 test functions |
