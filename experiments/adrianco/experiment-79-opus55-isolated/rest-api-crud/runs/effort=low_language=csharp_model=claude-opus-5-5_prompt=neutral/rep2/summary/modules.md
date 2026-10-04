# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BooksApi/Program.cs | Minimal-API host: DI wiring + 6 route handlers | top-level statements, `Program` (partial) |
| src/BooksApi/BookStore.cs | SQLite-backed persistence (connection per op) | `BookStore`, `List`, `Get`, `Create`, `Update`, `Delete` |
| src/BooksApi/Book.cs | Domain record + request DTO with validation | `Book`, `BookInput`, `BookInput.Validate()` |
| tests/BooksApi.Tests/BooksApiTests.cs | In-memory integration tests via WebApplicationFactory | `ApiFactory`, `BooksApiTests` (10 Facts + 1 Theory×5) |
