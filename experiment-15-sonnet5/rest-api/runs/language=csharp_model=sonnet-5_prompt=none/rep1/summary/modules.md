# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookCollection.Api/Program.cs | Minimal-API host: DI/DB setup, route handlers, validation helpers | top-level statements, `Validate()`, `ToErrorDictionary()`, `partial class Program` |
| src/BookCollection.Api/Models/Book.cs | EF Core entity persisted to SQLite | `Book` (Id, Title, Author, Year?, Isbn?) |
| src/BookCollection.Api/Models/BookDtos.cs | Request DTO with DataAnnotations validation | `BookRequest` ([Required] Title/Author) |
| src/BookCollection.Api/Data/BookDbContext.cs | EF Core DbContext | `BookDbContext`, `Books` DbSet |
| tests/BookCollection.Tests/BooksApiTests.cs | xUnit integration tests | 7 `[Fact]` methods |
| tests/BookCollection.Tests/ApiFactory.cs | WebApplicationFactory harness with in-memory SQLite | `ApiFactory` |
