# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, routing, handlers, JSON/error helpers, input validation | `main()`, `API.routes()`, `API.create/list/get/update/delete` |
| store.go | SQLite persistence layer and `Book` model | `Book`, `Store`, `NewStore()`, `Create/List/Get/Update/Delete` |
| main_test.go | httptest-based API integration tests | 4 test functions (`TestHealth`, `TestCRUD`, `TestValidation`, `TestListAuthorFilter`) |
