# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| BooksApi/Program.cs | Minimal-API host: route handlers + validation | top-level statements, `IsValid`, `ValidationError`, `Program` |
| BooksApi/Data/BookRepository.cs | SQLite persistence (schema init + CRUD) | `BookRepository`, `InitializeAsync`, `CreateAsync`, `ListAsync`, `GetAsync`, `UpdateAsync`, `DeleteAsync` |
| BooksApi/Models/Book.cs | Domain records | `Book`, `BookInput` |
| BooksApi.Tests/BooksApiIntegrationTests.cs | HTTP integration tests | `BooksApiIntegrationTests` (4 `[Fact]`), `BookApiFactory` |
