# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | HTTP server bootstrap, route registration on `net/http` mux | `main()` |
| handlers.go | Request handlers for books/health, validation, response wiring | `BookHandler`, `NewBookHandler()`, `Health`, `HandleBooks`, `HandleBookByID` |
| database.go | SQLite-backed CRUD store and schema setup | `BookStore`, `NewBookStore()`, `CreateBook`, `GetAllBooks`, `GetBookByID`, `UpdateBook`, `DeleteBook`, `ErrNotFound` |
| models.go | Data types and JSON response helpers | `Book`, `CreateBookRequest`, `ErrorResponse`, `ValidationError`, `ValidationErrorsBody`, `writeJSON()`, `writeError()` |
| main_test.go | httptest-based integration tests | 11 test functions |
| go.mod | Module definition (Go module `book-api`) | — |
| go.sum | Dependency checksums | — |
| README.md | Setup and run instructions | — |
