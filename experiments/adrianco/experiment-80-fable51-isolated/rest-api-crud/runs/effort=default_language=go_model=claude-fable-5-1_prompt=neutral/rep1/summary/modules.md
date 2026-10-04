# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: opens store, starts HTTP server, env config | `main()`, `envOr()` |
| handlers.go | HTTP handler, routing, request decode/validation, JSON responses | `NewHandler()`, `api`, `decodeBook()`, `parseID()`, `writeJSON()` |
| store.go | SQLite persistence layer and `Book` model | `NewStore()`, `Store`, `Book`, `ErrNotFound` |
| handlers_test.go | End-to-end HTTP handler tests against in-memory SQLite | 9 test functions |
