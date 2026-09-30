# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry: opens the store and serves HTTP with a read-header timeout | `main()`, `getenv()` |
| handlers.go | HTTP routing, JSON encoding, request validation, per-route handlers | `NewHandler()`, `api`, `decodeBook()`, `parseID()` |
| store.go | SQLite persistence: schema migration and CRUD | `Book`, `Store`, `NewStore()`, `ErrNotFound`, `Create/List/Get/Update/Delete` |
| handlers_test.go | HTTP integration tests via `httptest` | 7 test functions |
