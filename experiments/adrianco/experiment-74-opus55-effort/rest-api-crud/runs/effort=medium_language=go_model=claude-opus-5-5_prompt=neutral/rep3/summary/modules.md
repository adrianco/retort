# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry point: opens store, wires HTTP server, graceful shutdown | `main()`, `envOr()` |
| store.go | SQLite persistence layer for books (schema + CRUD) | `Book`, `Store`, `OpenStore()`, `Create/List/Get/Update/Delete`, `ErrNotFound` |
| handlers.go | HTTP routing, request decoding, validation, JSON responses | `NewServer()`, `bookInput`, `handler`, `validISBN()`, `writeJSON()` |
| main_test.go | Integration + unit tests against `httptest` server | 8 test functions |
