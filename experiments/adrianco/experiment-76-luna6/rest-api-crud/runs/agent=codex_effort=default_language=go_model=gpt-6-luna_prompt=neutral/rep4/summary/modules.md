# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: opens SQLite, runs migration, starts HTTP server | `main()` |
| books.go | HTTP handlers, routing, SQLite persistence, validation, JSON helpers | `newServer()`, `initialize()`, `Book` |
| books_test.go | httptest-based integration tests over the real handler | 3 test functions |
