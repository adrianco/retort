# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entry: flag parsing, DB open, graceful HTTP shutdown | `main()`, `run()` |
| server.go | Route wiring, middleware, JSON/error writers | `newServer()`, `writeJSON()`, `writeError()`, `logRequests()`, `recoverPanics()` |
| handlers.go | HTTP handlers for all CRUD + health routes, body decode/validate | `api` (health/listBooks/getBook/createBook/updateBook/deleteBook) |
| store.go | SQLite persistence layer (CRUD, schema, scanning) | `Store`, `OpenStore()`, `Create/Get/List/Update/Delete`, `ErrNotFound` |
| book.go | Domain model + input validation (title/author/year/ISBN) | `Book`, `BookInput`, `validateBook()`, `validISBN()` |
| api_test.go | HTTP integration tests over a live httptest server | 11 test functions |
| book_test.go | Validation + ISBN unit tests | 5 test functions |
| store_test.go | Store CRUD / filter / persistence tests | 4 test functions |
