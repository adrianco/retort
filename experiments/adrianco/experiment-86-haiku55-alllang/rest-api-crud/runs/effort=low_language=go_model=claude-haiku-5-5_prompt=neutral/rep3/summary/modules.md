# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `main.go` | Entry point: reads config from env, opens the store, runs the HTTP server | `main()` |
| `handlers.go` | HTTP routing, request decoding, validation, JSON responses | `NewServer()`, `Server.ServeHTTP`, `bookInput.Validate` |
| `store.go` | SQLite schema and data access | `OpenStore()`, `Store` (`Create`/`Get`/`List`/`Update`/`Delete`/`Ping`/`Close`), `Book` |
| `server_test.go` | HTTP-level tests exercising all endpoints against an in-memory DB | 6 test functions |
