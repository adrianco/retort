# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookApi/Program.cs | Minimal-API host, route handlers, model records, SQLite repository | `MapGet/MapPost/MapPut/MapDelete` routes, `Book`, `BookInput`, `BookRepository`, `Program` |
| tests/BookApi.Tests/BooksApiTests.cs | WebApplicationFactory integration tests | `BooksApiTests` (5 `[Fact]` methods), `Factory` |
