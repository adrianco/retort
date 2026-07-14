# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| BookApi/Program.cs | Minimal-API host, EF Core wiring, all route handlers, request DTO + validation | top-level statements, `BookCreateRequest`, `BookCreateRequest.IsValid()`, `partial class Program` |
| BookApi/Book.cs | Book entity model | `Book` |
| BookApi/BookDbContext.cs | EF Core DbContext exposing the Books set | `BookDbContext`, `Books` |
| BookApi.Tests/BooksApiTests.cs | Integration tests for the /books CRUD + validation surface | 12 `[Fact]` tests, `BookDto` |
| BookApi.Tests/HealthCheckTests.cs | Integration test for /health | 1 `[Fact]` test |
| BookApi.Tests/AppStartupTests.cs | Regression test: schema is created against a fresh on-disk DB at real startup | 1 `[Fact]` test |
| BookApi.Tests/CustomWebApplicationFactory.cs | Test host swapping SQLite to a shared in-memory connection | `CustomWebApplicationFactory` |
