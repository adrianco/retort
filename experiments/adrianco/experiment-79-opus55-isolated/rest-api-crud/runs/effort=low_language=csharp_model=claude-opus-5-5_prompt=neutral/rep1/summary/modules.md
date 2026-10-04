# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookApi/Program.cs | ASP.NET Core minimal-API host: route mapping, error middleware, DI wiring | top-level statements, `NotFound()`, `public partial class Program` |
| src/BookApi/BookRepository.cs | SQLite-backed storage; opens a connection per operation, creates schema on init | `Create`, `List`, `Get`, `Update`, `Delete`, `Ping` |
| src/BookApi/Book.cs | Domain record + request DTO with validation | `Book`, `BookInput`, `BookInput.Validate()` |
| src/BookApi/appsettings.json | Logging + `Database:Path` configuration | — |
| tests/BookApi.Tests/BooksApiTests.cs | xUnit in-process integration tests against a throwaway SQLite file | `ApiFactory`, `BooksApiTests` (11 test methods) |
