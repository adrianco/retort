# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server bootstrap, route registration (net/http ServeMux) | `main()` |
| handlers.go | HTTP handlers for all book endpoints | `API`, `NewAPI()`, `HealthCheck`, `CreateBook`, `ListBooks`, `GetBook`, `UpdateBook`, `DeleteBook` |
| models.go | Book domain types + SQLite-backed store (CRUD) | `Book`, `CreateBookRequest`, `UpdateBookRequest`, `BookStore`, `NewBookStore()`, `Create`, `GetAll`, `GetByID`, `Update`, `Delete`, `Close` |
| main_test.go | HTTP handler + store integration tests | 9 test functions |
