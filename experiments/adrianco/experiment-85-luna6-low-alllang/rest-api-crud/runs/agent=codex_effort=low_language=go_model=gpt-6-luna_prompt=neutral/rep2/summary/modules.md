# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, routing, CRUD handlers, SQLite access, validation | `main()`, `API.ServeHTTP`, `openDB()`, `Book` |
| main_test.go | httptest-based API integration tests | 3 test functions (`TestCreateAndGetBook`, `TestListAuthorFilterAndValidation`, `TestUpdateDeleteAndHealth`) |
| go.mod / go.sum | Module definition + pinned deps (`modernc.org/sqlite`) | — |
| README.md | Setup, run and API docs | — |
