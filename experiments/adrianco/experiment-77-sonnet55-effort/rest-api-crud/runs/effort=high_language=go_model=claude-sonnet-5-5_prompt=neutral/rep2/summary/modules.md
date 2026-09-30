# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: config from env, opens Store, runs http.Server with graceful shutdown | `main`, `getenv` |
| handlers.go | HTTP router + handlers, JSON encoding, request decode/validation | `NewHandler`, `api`, `decodeBook`, `parseID` |
| store.go | SQLite persistence layer + Book model | `Store`, `Book`, `OpenStore`, `ErrNotFound`, CRUD methods |
| handlers_test.go | End-to-end API tests via httptest server + a persistence test | 6 test functions |
