# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, router, request handlers, validation | `newHandler()`, `main()`, `server` |
| store.go | SQLite persistence layer and Book model | `Book`, `Store`, `NewStore()` |
| main_test.go | API integration tests over `httptest` | 4 test functions |
