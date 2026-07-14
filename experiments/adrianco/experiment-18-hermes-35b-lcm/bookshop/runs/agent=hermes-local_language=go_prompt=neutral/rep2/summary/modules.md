# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry: opens DB, registers routes, starts `net/http` server | `main()` |
| handlers.go | HTTP layer: routing + per-endpoint handlers + create-validation | `Server`, `NewServer`, `HandleHealth`, `HandleBooks`, `HandleCreateBook`, `HandleListBooks`, `HandleGetBook`, `HandleUpdateBook`, `HandleDeleteBook`, `validateCreate` |
| database.go | Persistence: SQLite connection, table DDL, CRUD queries | `Database`, `NewDatabase`, `CreateBook`, `GetAllBooks`, `GetBook`, `UpdateBook`, `DeleteBook`, `Close` |
| model.go | Data types: request/response DTOs | `Book`, `CreateBookRequest`, `UpdateBookRequest`, `ValidationError`, `ErrorResponse`, `HealthResponse` |
| handler_test.go | Integration tests over the HTTP handlers (in-memory DB) | 17 `Test*` functions, `setupTestDB`, `doRequest` |
