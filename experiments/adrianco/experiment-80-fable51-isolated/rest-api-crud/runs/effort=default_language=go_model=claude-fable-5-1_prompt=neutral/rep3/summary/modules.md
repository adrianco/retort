# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry point: reads `ADDR`/`DB_PATH`, opens the store, starts an `http.Server` | `main()`, `getenv()` |
| handlers.go | HTTP layer: routing, request decoding/validation, JSON responses | `NewHandler()`, `Server`, `bookInput`, handler methods |
| store.go | SQLite persistence layer and the `Book` model | `NewStore()`, `Store`, `Book`, `ErrNotFound` |
| main_test.go | HTTP integration tests against an in-memory SQLite store | 6 test functions |
