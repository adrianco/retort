# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry point: opens SQLite DB, wires store + API, starts HTTP server | `main()` |
| models.go | `Book` domain type and required-field validation | `Book`, `Book.Validate()` |
| store.go | SQLite-backed CRUD data access + schema migration | `Store`, `NewStore()`, `Create`, `List`, `Get`, `Update`, `Delete`, `ErrNotFound` |
| handlers.go | HTTP handlers, route table, JSON/error helpers | `API`, `NewAPI()`, `Routes()`, per-route handlers |
| api_test.go | BDD-style HTTP integration tests against in-memory SQLite | 11 test functions |
