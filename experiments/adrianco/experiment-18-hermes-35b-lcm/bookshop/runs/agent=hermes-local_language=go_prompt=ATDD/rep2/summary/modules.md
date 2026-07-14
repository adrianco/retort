# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Wires repository + app, registers routes, starts HTTP server | `main()` |
| app.go | HTTP handlers for health and book CRUD | `App`, `HealthCheck`, `handleBooks`, `handleBookByID` |
| book.go | Book model and validation | `Book`, `BookValidationErrors`, `Validate()` |
| repository.go | SQLite persistence + schema init | `BookRepository`, `NewBookRepository()`, `CreateBook`, `GetAllBooks`, `GetBookByID`, `UpdateBook`, `DeleteBook`, `Close` |
| acceptance_test.go | End-to-end HTTP acceptance tests via httptest | 19 test functions |
| book_test.go | Unit tests for Book validation | 5 test functions |
| repository_test.go | Unit tests for SQLite repository | 9 test functions |
