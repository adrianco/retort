# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry point: config from env, opens store, runs HTTP server with graceful shutdown | `main()`, `getenv()` |
| store.go | SQLite persistence layer (schema, CRUD) using pure-Go `modernc.org/sqlite` | `Book`, `Store`, `NewStore()`, `Create/List/Get/Update/Delete`, `Ping()`, `ErrNotFound` |
| handlers.go | HTTP server: routing, request decode/validation, JSON responses, error mapping | `Server`, `NewServer()`, `Routes()`, handlers, `decodeBook()`, `parseID()` |
| handlers_test.go | HTTP integration tests against an in-memory (and one on-disk) DB | 10 test functions |
