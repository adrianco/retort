# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookApi/Program.cs | ASP.NET Core minimal-API host; wires DI and maps all routes | `Program`, `BuildApp()` |
| src/BookApi/Book.cs | Domain + request records | `Book`, `BookInput` |
| src/BookApi/BookValidator.cs | Field-level input validation (title/author/year/ISBN) | `BookValidator.Validate()`, `IsValidIsbn()` |
| src/BookApi/IBookRepository.cs | Persistence abstraction | `IBookRepository` |
| src/BookApi/SqliteBookRepository.cs | SQLite-backed CRUD, creates schema on construction | `SqliteBookRepository` |
| tests/BookApi.Tests/BookApiTests.cs | HTTP integration tests via `WebApplicationFactory` | 6 test methods |
| tests/BookApi.Tests/BookValidatorTests.cs | Validator unit tests | 3 test methods (1 `[Theory]`, 5 cases) |
