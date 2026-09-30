# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entrypoint: flag/env config, opens store, starts `http.Server` | `main()`, `getenv()` |
| handlers.go | HTTP routing + request handlers, JSON encoding, input validation | `API`, `API.Handler()`, `decodeBook()` |
| store.go | SQLite persistence layer and `Book` model | `Store`, `NewStore()`, `Book`, `ErrNotFound` |
| api_test.go | HTTP integration tests via `httptest` | 7 test functions |
