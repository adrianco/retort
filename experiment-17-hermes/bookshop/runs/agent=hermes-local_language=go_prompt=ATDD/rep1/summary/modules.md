# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: init DB, init router, start HTTP server on `$PORT`/8080 | `main()` |
| database.go | SQLite connection + `books` table migration; `Book` model | `initDB()`, `Book` |
| router.go | gorilla/mux router; wires `/books`, `/books/{id}`, `/health` | `initRouter(db)` |
| handlers.go | CRUD + list/filter HTTP handlers | `getBooks`, `getBook`, `createBook`, `updateBook`, `deleteBook` |
| main_test.go | API tests via httptest (health, create, list, get) | `TestBookAPI` (4 subtests) |
| integration_test.go | Full CRUD flow + author-filter tests via httptest | `TestBookAPIIntegration` (2 subtests) |
