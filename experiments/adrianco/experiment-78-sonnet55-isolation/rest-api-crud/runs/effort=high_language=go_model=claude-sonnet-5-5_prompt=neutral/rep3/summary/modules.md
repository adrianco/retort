# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: env config, HTTP server wiring, graceful shutdown | `main()`, `getenv()` |
| server.go | HTTP handler, routing, request decode/validate, JSON responses | `NewHandler()`, `Server`, `bookInput` |
| store.go | SQLite persistence + schema/migration and CRUD | `NewStore()`, `Store`, `Book`, `ErrNotFound` |
| server_test.go | HTTP integration tests over `httptest.Server` | 8 test functions |
