# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Server bootstrap: opens DB, wires gorilla/mux routes, listens | `main()` |
| models.go | Data types and request/response DTOs | `Book`, `CreateBookRequest`, `UpdateBookRequest`, `ErrorResponse` |
| handlers.go | HTTP handlers + JSON helpers | `Handler`, `HealthCheck`, `CreateBook`, `ListBooks`, `GetBook`, `UpdateBook`, `DeleteBook` |
| database.go | SQLite persistence layer | `Database`, `NewDatabase()`, `CreateBook`, `GetBookByID`, `ListBooks`, `UpdateBook`, `DeleteBook` |
| handlers_test.go | HTTP handler integration tests | 14 test functions |
