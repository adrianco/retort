# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry: parses flags/env, opens store, serves HTTP with graceful shutdown | `main()`, `run()` |
| internal/book/book.go | Book domain type + input validation (title/author required, year/ISBN checks, ISBN normalization) | `Book`, `Validate()`, `ValidationError` |
| internal/store/store.go | SQLite-backed repository (modernc.org/sqlite), schema, CRUD + author filter | `Store`, `Open()`, `Create/Get/List/Update/Delete`, `ErrNotFound` |
| internal/api/server.go | JSON REST handlers, routing (net/http ServeMux), error/JSON helpers | `NewHandler()`, `Server` |
| internal/book/book_test.go | Validation unit tests | 2 test functions |
| internal/store/store_test.go | Store CRUD + persistence tests | 7 test functions |
| internal/api/server_test.go | HTTP API integration tests | 14 test functions |
