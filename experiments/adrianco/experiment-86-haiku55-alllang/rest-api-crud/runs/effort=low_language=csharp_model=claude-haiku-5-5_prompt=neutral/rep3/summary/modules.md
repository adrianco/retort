# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BookApi/Program.cs | ASP.NET Core minimal-API host; maps `/health` and the `/books` route group | top-level statements, `public partial class Program` |
| src/BookApi/Book.cs | Domain records and request validation | `Book`, `BookRequest`, `BookValidator.Validate` |
| src/BookApi/BookRepository.cs | SQLite-backed persistence via Microsoft.Data.Sqlite (ADO.NET) | `IBookRepository`, `SqliteBookRepository` |
| src/BookApi/appsettings.json | Logging + AllowedHosts config | (config) |
| src/BookApi/BookApi.csproj | Web SDK project, net10.0, 1 package | (project) |
| tests/BookApi.Tests/BooksApiTests.cs | xUnit integration tests hosting the app with `WebApplicationFactory` | `BookApiFactory`, `BooksApiTests` (8 test attributes) |
| tests/BookApi.Tests/BookApi.Tests.csproj | Test project, net10.0, Mvc.Testing + xunit | (project) |
