# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: opens SQLite via `DB_PATH`, binds `ADDR`, starts HTTP server | `main()` |
| server.go | HTTP server, `Book` model, route handlers, JSON/validation helpers | `Server`, `NewServer()`, `ServeHTTP()`, `Book` |
| server_test.go | httptest-based integration tests over the router | 4 test functions |
