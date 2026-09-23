# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookApi/Program.cs | Minimal-API host, route handlers, models, SQLite repository | `app`, `Book`, `BookInput`, `BookRepository`, `Program` |
| tests/BookApi.Tests/BooksApiTests.cs | `WebApplicationFactory` integration tests over an in-memory shared-cache SQLite DB | `BooksApiTests` (6 test methods) |
| src/BookApi/BookApi.csproj | Web SDK project (net10.0), depends on `Microsoft.Data.Sqlite` | — |
| tests/BookApi.Tests/BookApi.Tests.csproj | Test project (xunit + `Mvc.Testing`) | — |
| BookApi.slnx | Solution wiring app + test projects | — |
| README.md | Setup, run, endpoint and test instructions | — |
