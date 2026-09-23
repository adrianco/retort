# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: env config, opens store, starts HTTP server with graceful shutdown | `main()`, `getenv()` |
| store.go | SQLite persistence layer (modernc.org/sqlite, pure Go) | `Book`, `Store`, `NewStore()`, `Create/List/Get/Update/Delete` |
| handlers.go | HTTP routing, request decoding, validation, JSON responses | `Server`, `NewServer()`, `bookInput`, `validISBN()` |
| main_test.go | Integration + unit tests over the HTTP surface and store | 7 test functions |
