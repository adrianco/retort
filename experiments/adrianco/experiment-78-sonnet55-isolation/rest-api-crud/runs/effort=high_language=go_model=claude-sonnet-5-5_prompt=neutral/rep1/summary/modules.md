# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry: opens the store, wires the HTTP server, reads `ADDR`/`DB_PATH` | `main`, `getenv` |
| handlers.go | HTTP layer: route table, JSON encoding, request validation, per-endpoint handlers | `NewHandler`, `api`, `decodeBook`, `parseID` |
| store.go | SQLite persistence: schema migration and CRUD queries | `NewStore`, `Store`, `Book`, `ErrNotFound` |
| api_test.go | Integration tests through `httptest` | 6 test functions |
