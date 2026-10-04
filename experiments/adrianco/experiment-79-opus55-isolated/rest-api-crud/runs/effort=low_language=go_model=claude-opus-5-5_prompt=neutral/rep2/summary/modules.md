# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: env config, opens store, starts `http.Server` | `main()`, `envOr()` |
| store.go | SQLite persistence layer for books | `Book`, `Store`, `NewStore()`, `ErrNotFound` |
| handlers.go | HTTP routing, request decode/validate, JSON responses | `NewHandler()`, `api`, `bookInput` |
| handlers_test.go | HTTP integration tests against in-memory SQLite | 8 test functions |
