# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| BookCollection.Api/Program.cs | App wiring: SQLite DbContext, controllers, `/health` minimal endpoint | top-level statements, `Program` (partial, for tests) |
| BookCollection.Api/Controllers/BooksController.cs | CRUD route handlers for `/books` | `GetAll`, `GetById`, `Create`, `Update`, `Delete` |
| BookCollection.Api/Data/BookDbContext.cs | EF Core DbContext | `BookDbContext`, `Books` DbSet |
| BookCollection.Api/Models/Book.cs | Persistence entity | `Book` |
| BookCollection.Api/Models/BookDtos.cs | Request/response DTOs with validation | `CreateBookRequest`, `UpdateBookRequest`, `BookDto` |
| BookCollection.Tests/BooksApiTests.cs | Integration tests via WebApplicationFactory | 10 `[Fact]` methods, `BookResponse` |
