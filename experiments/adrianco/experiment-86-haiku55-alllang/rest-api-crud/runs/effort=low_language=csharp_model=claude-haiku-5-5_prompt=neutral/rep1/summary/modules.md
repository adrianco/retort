# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Program.cs | Minimal-API host; maps all HTTP endpoints and wires the repository | top-level statements, `public partial class Program` |
| Book.cs | Domain record + request DTO + validation rules | `Book`, `BookRequest`, `BookValidator.Validate`, `BookValidator.ToBook` |
| BookRepository.cs | SQLite data access (raw SQL, connection-per-op) | `BookRepository`, `Initialize`, `Ping`, `Add`, `Get`, `List`, `Update`, `Delete` |
| tests/BookApi.Tests/BooksApiTests.cs | xUnit integration tests via WebApplicationFactory | `BooksApiFactory`, `BooksApiTests` (9 `[Fact]` methods) |
