# Summary: effort=low language=csharp model=claude-opus-5-5 prompt=neutral · rep 3

- **Shape:** ASP.NET Core (.NET 10) minimal API with a hand-rolled `Microsoft.Data.Sqlite` repository.
- **Structure:** 2 source files (1 app, 1 test), single-project API + xUnit test project.
- **Interfaces:** 6 HTTP routes (5 CRUD + health), 1 SQLite table, `BookRepository` with 5 methods.
- **Notable:** Whole app in one 139-line `Program.cs`; parameterized SQL throughout, per-request connections, and an in-memory-DB keep-alive trick so `WebApplicationFactory` tests run against a shared in-memory SQLite. Adds a year-range validation beyond the spec.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
