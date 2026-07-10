# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite store, and all route handlers | `main()`, `NewBookStore()`, `BookStore` (CRUD methods), `handle*` handlers |
| main_test.go | httptest-based integration tests exercising the handlers | `TestBookAPI` (8 `t.Run` subtests) |

Notes:
- Single-package (`package main`) Go project; no separate model/db/router modules — everything lives in `main.go`.
- `BookStore` bundles both persistence (`CreateBook`, `GetBooks`, `GetBook`, `UpdateBook`, `DeleteBook`, `HealthCheck`) and HTTP handling.
- Two parallel handler sets exist for `/books/{id}`: the standalone `handleGetBook`/`handleUpdateBook`/`handleDeleteBook` (parse the path themselves) and the `handle*WithID` variants (take an `id int`). `main()` wires the `WithID` set; the tests call the standalone set.
