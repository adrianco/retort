# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: opens store, starts `net/http` server, graceful shutdown on SIGINT/SIGTERM | `main()`, `envOr()` |
| handlers.go | HTTP routing, request decoding, validation, JSON responses | `NewServer()`, `server` methods, `bookInput.validate()`, `validISBN()`, `writeJSON()` |
| store.go | SQLite persistence layer (modernc pure-Go driver) | `OpenStore()`, `Store` (`Create`/`List`/`Get`/`Update`/`Delete`/`Ping`), `Book`, `ErrNotFound` |
| api_test.go | HTTP integration tests against a temp SQLite file | 6 test functions |
