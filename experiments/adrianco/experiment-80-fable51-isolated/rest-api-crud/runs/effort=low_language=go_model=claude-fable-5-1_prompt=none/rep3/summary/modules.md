# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, SQLite access, route handlers, validation | `main()`, `OpenDB()`, `NewServer()`, `Server.Handler()`, `Book` |
| main_test.go | httptest-based API integration tests | 6 test functions (`TestHealth`, `TestCreateAndGetBook`, `TestCreateValidation`, `TestListWithAuthorFilter`, `TestUpdateBook`, `TestDeleteBook`) |
| README.md | Setup/run/test docs, endpoint + JSON reference | — |
| go.mod / go.sum | Module definition and dependency lock (`modernc.org/sqlite`) | — |
