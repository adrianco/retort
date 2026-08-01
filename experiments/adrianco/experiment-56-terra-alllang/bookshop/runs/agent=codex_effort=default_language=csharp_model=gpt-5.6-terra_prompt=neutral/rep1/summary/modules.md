# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| BookCollection.Api/Program.cs | ASP.NET Core minimal-API host: config, DI wiring, DB init, and all route handlers | top-level statements, `Validate()`, `partial class Program` |
| BookCollection.Api/Data/BookRepository.cs | SQLite data access; CRUD + author filter over the `Books` table | `BookRepository`, `InitializeAsync`, `CreateAsync`, `GetAllAsync`, `GetByIdAsync`, `UpdateAsync`, `DeleteAsync` |
| BookCollection.Api/Models/Book.cs | Domain records for stored book and request input | `Book`, `BookInput` |
| BookCollection.Api/appsettings.json | Runtime configuration (logging, allowed hosts) | (config) |
| BookCollection.Api/appsettings.Development.json | Development logging overrides | (config) |
| BookCollection.Api/Properties/launchSettings.json | Launch profiles / URLs | (config) |
| BookCollection.Api/BookCollection.Api.csproj | Web SDK project; net10.0, `Microsoft.Data.Sqlite` 10.0.0 | (build) |
| BookCollection.Tests/BookRepositoryTests.cs | xUnit integration tests exercising the repository against a temp SQLite file | 4 test methods (`BookRepositoryTests`) |
| BookCollection.Tests/BookCollection.Tests.csproj | Test project | (build) |
| BookCollection.slnx | Solution file linking API + Tests projects | (build) |
