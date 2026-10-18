# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, routing, CRUD handlers, SQLite access, validation | `main()`, `NewAPI()`, `OpenDB()`, `API.ServeHTTP` |
| main_test.go | httptest-based integration tests | 3 test functions (`TestCreateGetUpdateDeleteBook`, `TestListFilterAndRequiredFields`, `TestHealth`) |
