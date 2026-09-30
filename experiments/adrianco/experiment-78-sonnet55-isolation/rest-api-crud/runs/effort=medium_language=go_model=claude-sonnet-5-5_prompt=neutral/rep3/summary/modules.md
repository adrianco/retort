# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, routing, handlers, request validation | `newHandler()`, `main()` |
| store.go | SQLite persistence layer + `Book` model | `Book`, `Store`, `NewStore()` |
| main_test.go | httptest-based integration tests | 4 test functions |
