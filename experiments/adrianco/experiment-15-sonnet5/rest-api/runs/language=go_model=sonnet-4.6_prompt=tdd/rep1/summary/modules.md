# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: opens SQLite store, starts HTTP server | `main()` |
| book.go | `Book` domain model + JSON tags | `Book` |
| store.go | SQLite persistence behind a `store` interface | `store`, `sqliteStore`, `newSQLiteStore()`, `errNotFound` |
| handler.go | `net/http` router + CRUD/health handlers, JSON helpers | `newRouter()`, `handleCreateBook()` … `handleDeleteBook()`, `handleHealth()` |
| handler_test.go | Integration tests via `httptest.Server` against in-memory SQLite | 9 test functions |
