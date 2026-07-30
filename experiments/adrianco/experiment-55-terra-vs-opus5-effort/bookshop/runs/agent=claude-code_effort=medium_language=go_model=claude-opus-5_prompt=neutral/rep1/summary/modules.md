# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: config from env, opens store, runs HTTP server with graceful shutdown | `main`, `envOr` |
| book.go | Domain model + request validation | `Book`, `BookInput`, `ValidationError`, `BookInput.toBook` |
| server.go | HTTP routing and handlers (net/http ServeMux) | `Server`, `NewServer`, handlers, `writeJSON` |
| store.go | SQLite-backed persistence (CRUD + migrations) | `Store`, `OpenStore`, `Create/List/Get/Update/Delete`, `Ping` |
| server_test.go | HTTP integration tests via httptest | 12 test functions |
| store_test.go | Store-layer unit tests (incl. disk persistence) | 4 test functions |
