# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: config from env, opens store, wires handler, graceful shutdown | `main()`, `getenv()` |
| handlers.go | HTTP server: routing, request decode/validate, JSON responses | `NewHandler()`, `Server`, `bookInput` |
| store.go | SQLite persistence layer and the `Book` model | `NewStore()`, `Store`, `Book`, `ErrNotFound` |
| handlers_test.go | End-to-end HTTP handler tests against a real SQLite DB | 8 test functions |
