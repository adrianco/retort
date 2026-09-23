# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, routing, handlers, JSON/error helpers | `API.ServeHTTP`, `main()`, `writeJSON`, `writeError` |
| book.go | `Book` model, SQLite open/migrate, CRUD data access | `Book`, `openDatabase`, `createBook`, `getBook`, `listBooks`, `updateBook`, `deleteBook`, `ErrNotFound` |
| main_test.go | httptest integration tests over `API.ServeHTTP` | 4 test functions |
| README.md | Setup and run instructions | — |
| go.mod / go.sum | Module + `mattn/go-sqlite3` dependency | — |
