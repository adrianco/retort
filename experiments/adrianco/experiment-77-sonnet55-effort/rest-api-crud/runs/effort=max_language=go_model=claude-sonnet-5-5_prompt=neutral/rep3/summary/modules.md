# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry: config parsing, listener setup, graceful shutdown | `main`, `run`, `serve`, `parseConfig` |
| internal/api/api.go | HTTP handler wiring and route table | `New`, `BookStore` (interface), `routes` |
| internal/api/handlers.go | Per-endpoint handlers (CRUD, health, error mapping) | `health`, `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook` |
| internal/api/respond.go | JSON encode/decode, body limits, error shaping | `writeJSON`, `writeError`, `decodeInput`, `decodeJSON` |
| internal/api/middleware.go | Request logging + panic recovery, status recorder | `logAndRecover`, `statusRecorder` |
| internal/book/book.go | Domain model, normalization, validation rules | `Input`, `Book`, `Normalized`, `Validate`, `ValidationError` |
| internal/sqlite/store.go | SQLite persistence via pure-Go driver | `Open`, `Store`, `Create`, `Get`, `List`, `Update`, `Delete`, `Ping` |
| main_test.go | Config/serve/lifecycle tests | 6 test functions |
| internal/api/*_test.go | API handler, routing, failure, fuzz tests | ~45 test/fuzz functions |
| internal/book/book_test.go | Model/validation tests | 5 test functions |
| internal/sqlite/store_test.go | Persistence tests | ~22 test functions |

Non-test source files: main.go + 7 package files. Test files: 8 (`*_test.go`).
