# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Program entry: flag/env config, DB open, HTTP server lifecycle with graceful shutdown | `main`, `run`, `loadConfig` |
| internal/api/api.go | Route table and handler wiring; `BookStore` dependency interface | `New`, `BookStore` |
| internal/api/handlers.go | HTTP handlers for each endpoint plus id parsing and error mapping | `createBook`, `listBooks`, `getBook`, `updateBook`, `deleteBook`, `health` |
| internal/api/respond.go | JSON encoding, error responses, request-body decode + validate | `writeJSON`, `writeError`, `decodeInput`, `decodeJSON` |
| internal/api/middleware.go | Request logging, panic recovery, status recording | `observe`, `statusRecorder` |
| internal/book/book.go | Domain model, input normalization and validation rules | `Book`, `Input`, `Validate`, `Normalize`, `ErrNotFound`, `ValidationError` |
| internal/store/store.go | SQLite persistence (modernc.org/sqlite, no CGO) with CRUD + Ping | `Store`, `Open`, `Create`, `Get`, `List`, `Update`, `Delete`, `Ping` |
| main_test.go | End-to-end + config + signal tests | 8 test functions |
| internal/api/api_test.go | HTTP-level handler tests | 26 test functions |
| internal/api/failure_test.go | Store-failure / panic / logging tests | 6 test functions |
| internal/api/middleware_test.go | Middleware behaviour tests | 4 test functions |
| internal/book/book_test.go | Validation/normalization tests | 3 test functions |
| internal/store/store_test.go | Store CRUD, concurrency, persistence tests | 15 test functions |

Non-test source: 759 LOC across 7 files. Tests: 1826 LOC across 6 files.
