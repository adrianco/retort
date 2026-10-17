# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: config via env, open store, graceful shutdown | `main`, `envOr` |
| api.go | HTTP server, route wiring, handlers, JSON helpers | `Server`, `NewServer`, `ServeHTTP` |
| store.go | SQLite persistence (CRUD + author filter), schema | `Store`, `OpenStore`, `Create/Get/List/Update/Delete` |
| book.go | Domain model, request input, normalization & validation | `Book`, `BookInput`, `Validate`, `ErrNotFound` |
| api_test.go | HTTP integration tests via httptest | 6 test functions |
