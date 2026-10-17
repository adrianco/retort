# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry: flag parsing, server wiring, graceful shutdown | `main()`, `run()` |
| api.go | HTTP handler, routing, method dispatch, JSON encode/decode, error responses | `NewHandler()`, `route()`, `api` |
| store.go | SQLite persistence (modernc.org/sqlite): schema, CRUD, author filter | `OpenStore()`, `Store`, `ErrNotFound` |
| book.go | Domain model + input validation (required fields, year range, ISBN check digit) | `Book`, `bookInput`, `normalizeISBN()` |
| api_test.go | HTTP-level integration tests against a live handler | 10 test functions |
| store_test.go | Store persistence/CRUD tests against a temp SQLite file | 7 test functions |
| book_test.go | Validation/ISBN unit tests | 2 test functions |
