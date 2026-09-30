# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entrypoint: opens store, wires HTTP server, graceful shutdown | `main`, `run` |
| internal/api/api.go | HTTP routing and CRUD/health handlers | `New`, `BookStore` |
| internal/api/respond.go | JSON response + error helpers, 405 handler | `writeJSON`, `writeError`, `methodNotAllowed` |
| internal/api/middleware.go | Request logging + panic-to-500 recovery | `middleware`, `statusRecorder` |
| internal/store/store.go | SQLite-backed repository (modernc pure-Go driver) | `Open`, `Store` (Create/Get/List/Update/Delete/Ping) |
| internal/book/book.go | Book model + input validation | `Book`, `Input`, `Input.Clean`, `ValidationError`, `ErrNotFound` |
| internal/api/api_test.go | HTTP integration tests | 18 test functions |
| internal/store/store_test.go | Store persistence tests | 12 test functions |
| internal/book/book_test.go | Validation unit tests | 5 test functions |
