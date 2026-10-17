# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Configuration, server startup, graceful shutdown | `main()`, `envOr()` |
| server.go | HTTP handlers, request decoding, validation | `NewServer()`, `Server.ServeHTTP`, `decodeBook`, `validateBook` |
| store.go | SQLite persistence layer | `OpenStore()`, `Store`, `Book`, `ErrNotFound` |
| server_test.go | HTTP integration tests against a temp DB | 5 test functions |
