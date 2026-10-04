# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BooksApi/Program.cs | ASP.NET Core minimal-API host; maps all HTTP routes | top-level statements, `Program` (partial) |
| src/BooksApi/Book.cs | Domain record + input DTO with validation | `Book`, `BookInput`, `BookInput.Validate()` |
| src/BooksApi/BookRepository.cs | SQLite persistence + schema bootstrap | `BookRepository`, `List`, `Get`, `Create`, `Update`, `Delete` |
| tests/BooksApi.Tests/BooksApiTests.cs | In-process integration tests | `ApiFactory`, `BooksApiTests` (9 test methods) |
