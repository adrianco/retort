# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry point, config from env, graceful shutdown | `main()`, `getenv()` |
| handlers.go | HTTP routing, request validation, JSON responses | `Server`, `Server.Routes()`, `bookInput`, `validISBN()` |
| store.go | SQLite persistence layer for books | `Store`, `OpenStore()`, `Book`, `ErrNotFound` |
| main_test.go | HTTP integration tests over the handler | 5 test functions |
