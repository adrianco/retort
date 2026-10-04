# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Config from env, HTTP server startup, graceful shutdown | `main`, `envOr` |
| handlers.go | Routing, request decoding/validation, JSON responses, JSON-ified 404/405 | `Server`, `NewServer`, `Handler`, `handle*` |
| store.go | SQLite schema and CRUD queries | `Store`, `NewStore`, `Book`, `ErrNotFound`, `Create`/`List`/`Get`/`Update`/`Delete`/`Ping` |
| handlers_test.go | HTTP integration tests | 11 test functions |
