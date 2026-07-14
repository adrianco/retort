# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookApi/Program.cs | App bootstrap: DI, SQLite DbContext, controllers, schema creation | top-level statements, `public partial class Program` |
| src/BookApi/Controllers/BooksController.cs | CRUD route handlers for `/books` | `CreateBook`, `ListBooks`, `GetBook`, `UpdateBook`, `DeleteBook` |
| src/BookApi/Controllers/HealthController.cs | Health-check route `/health` | `Get` |
| src/BookApi/Models/Book.cs | EF Core entity | `Book` |
| src/BookApi/Dtos/BookDtos.cs | Request/response DTOs + validation attributes | `BookRequest`, `BookResponse` |
| src/BookApi/Data/BookDbContext.cs | EF Core DbContext | `BookDbContext`, `Books` |
| tests/BookApi.Tests/BookApiFactory.cs | Test host over shared in-memory SQLite | `BookApiFactory`, `ResetDatabase()` |
| tests/BookApi.Tests/BooksEndpointsTests.cs | BDD integration tests for `/books` | 9 test methods (10 cases with Theory data) |
| tests/BookApi.Tests/HealthEndpointTests.cs | BDD integration test for `/health` | 1 test method |
