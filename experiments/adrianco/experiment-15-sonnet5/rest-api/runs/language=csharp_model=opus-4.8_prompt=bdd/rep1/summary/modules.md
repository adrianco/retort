# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookApi/Program.cs | ASP.NET Core Minimal API — endpoint definitions, app wiring, validation | top-level statements, `Validate()`, `partial class Program` |
| src/BookApi/Models/Book.cs | Book entity + create/update DTO | `Book`, `BookInput` |
| src/BookApi/Data/BookDbContext.cs | EF Core DbContext exposing the Books set | `BookDbContext`, `Books` |
| tests/BookApi.Tests/BooksApiTests.cs | xUnit integration tests (BDD style) + in-memory SQLite test host | `BookApiFactory`, `BooksApiTests` (8 `[Fact]` tests) |
