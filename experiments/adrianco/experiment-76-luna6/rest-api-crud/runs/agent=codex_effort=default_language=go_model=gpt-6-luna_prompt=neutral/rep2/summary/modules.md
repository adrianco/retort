# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server, routing, handlers, SQLite persistence, validation | `main()`, `NewAPI()`, `API.ServeHTTP()`, `Book` |
| main_test.go | httptest-based integration tests | 4 test functions (`TestCreateListAndFilterBooks`, `TestValidationAndNotFound`, `TestUpdateAndDeleteBook`, `TestHealthCheck`) |
