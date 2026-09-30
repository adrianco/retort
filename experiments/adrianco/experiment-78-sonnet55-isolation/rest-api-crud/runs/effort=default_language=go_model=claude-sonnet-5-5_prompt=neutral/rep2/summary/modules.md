# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, routing, handlers, JSON/validation helpers | `main()`, `newHandler(*Store)`, `server` |
| store.go | SQLite persistence + `Book` model | `Book`, `Store`, `NewStore(dsn)`, CRUD methods |
| main_test.go | HTTP integration tests (in-memory SQLite) | 4 test functions |
