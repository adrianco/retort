# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entrypoint; reads `BOOKAPI_DSN`/`BOOKAPI_ADDR`, opens store, starts HTTP server | `main()` |
| server.go | HTTP routing, handlers, request validation, JSON helpers | `Server`, `NewServer()`, `ServeHTTP()` |
| store.go | SQLite-backed persistence (schema migration + CRUD) | `Store`, `NewStore()`, `Create/List/Get/Update/Delete`, `ErrNotFound` |
| book.go | The `Book` domain model | `Book` |
| server_test.go | BDD-style HTTP behaviour tests over an in-memory DB | 11 test functions |
