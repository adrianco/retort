# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry: flag/env config, slog logger, listener, graceful shutdown | `main`, `run` |
| internal/api/server.go | HTTP `Server`, ServeMux routing, middleware wiring | `Server`, `NewServer`, `WithClock`, `Option` |
| internal/api/handlers.go | CRUD + health handlers, path/query parsing | `handleHealth`, `handleCreateBook`, `handleListBooks`, `handleGetBook`, `handleUpdateBook`, `handleDeleteBook` |
| internal/api/decode.go | Strict JSON body decoding (content-type, unknown fields, size cap) | `decodeJSONBody` |
| internal/api/respond.go | JSON response writer + error→status mapping | `respond`, `respondError`, `ErrorResponse`, `errorf` |
| internal/api/middleware.go | Panic recovery, request logging, status recorder | `recoverPanic`, `logRequests`, `statusRecorder` |
| internal/books/book.go | Domain model + input validation | `Book`, `Input`, `Validate`, `ValidationError` |
| internal/books/store.go | SQLite-backed store (CRUD, schema, ISBN uniqueness) | `Store`, `Open`, `Create`, `Get`, `List`, `Update`, `Delete`, `Ping` |
| internal/books/isbn.go | ISBN-10/13 normalization + check-digit validation | `NormalizeISBN` |
| main_test.go | Config/run lifecycle tests | 4 test functions |
| internal/api/api_test.go | HTTP integration tests | 17 test functions |
| internal/books/store_test.go | Store persistence/concurrency tests | test functions |
| internal/books/book_test.go | Validation tests | test functions |
| internal/books/isbn_test.go | ISBN normalization tests | test functions |
