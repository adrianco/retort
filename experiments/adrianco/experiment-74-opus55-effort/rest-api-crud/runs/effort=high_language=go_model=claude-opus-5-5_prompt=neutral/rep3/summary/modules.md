# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Program entry: flag/env config, opens Store, starts `http.Server` with timeouts, graceful shutdown on SIGINT/SIGTERM | `main()`, `envOr()` |
| handlers.go | HTTP layer: `net/http` mux (Go 1.22 method/path patterns), route handlers, request decode + validation, JSON/error writers | `NewServer()`, `Server`, `bookInput`, `validISBN()` |
| store.go | Persistence: SQLite (`modernc.org/sqlite`) CRUD, schema bootstrap, author index | `OpenStore()`, `Store`, `Book`, `ErrNotFound` |
| api_test.go | Integration + unit tests against `httptest.Server` and `Store` | 8 test functions |
