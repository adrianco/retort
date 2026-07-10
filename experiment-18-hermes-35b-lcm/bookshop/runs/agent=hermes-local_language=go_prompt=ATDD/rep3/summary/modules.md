# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry point; opens SQLite `books.db`, wires server, listens on :8080 | `main()` |
| server.go | HTTP layer: router + gorilla/mux handlers for all routes | `Server`, `NewServer()`, `ServeHTTP()`, `handle*` |
| database.go | SQLite persistence; CRUD on the `books` table | `Database`, `NewDatabase()`, `CreateBook/GetBook/UpdateBook/DeleteBook/ListBooks/ListBooksByAuthor` |
| models.go | Domain model + validation | `Book`, `Book.Validate()` |
| server_test.go | HTTP acceptance tests (external-client, via `ServeHTTP`) | 14 `TestAcceptance_*` functions |
| database_test.go | Unit tests for the persistence layer | 7 `TestDatabase_*` functions |
| models_test.go | Unit tests for `Book.Validate` | 4 `TestModel_*` functions |
