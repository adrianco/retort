# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entry, flag parsing, HTTP server lifecycle + graceful shutdown | `main()`, `run()`, `envOr()` |
| book.go | Book domain type, input payload, normalization + validation | `Book`, `BookInput`, `Normalize()`, `Validate()` |
| store.go | SQLite persistence layer (CRUD + schema) | `Store`, `OpenStore()`, `Create/List/Get/Update/Delete`, `Ping()`, `ErrNotFound` |
| handlers.go | HTTP router, request handlers, JSON/error responses | `API`, `NewHandler()`, `readBookInput()`, `writeJSON()` |
| handlers_test.go | API integration tests via httptest | 8 test functions (many table subtests) |
| store_test.go | Store persistence + not-found + id-reuse tests | 3 test functions |
