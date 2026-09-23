# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookApi/Program.cs | ASP.NET Core Minimal API: route mapping, request records, SQLite repository | top-level statements, `Book`, `BookInput`, `BookRepository`, `Program` |
| tests/BookApi.Tests/BooksApiTests.cs | Integration tests via `WebApplicationFactory<Program>` | `BooksApiTests` (6 `[Fact]` methods) |
