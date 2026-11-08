# Summary: effort=low_language=csharp_model=claude-haiku-5-5_prompt=neutral · rep 1

- **Shape:** ASP.NET Core (.NET 10) minimal-API REST service with SQLite via raw `Microsoft.Data.Sqlite`.
- **Structure:** 3 source modules + 1 test file (9 xUnit integration tests).
- **Interfaces:** 6 HTTP routes (full CRUD on `/books` + `?author=` filter + `/health`); one `books` table.
- **Notable:** A repair run that lands cleanly — connection-per-operation SQLite, `problem+json` validation, ISBN-10/13 normalisation, and `WebApplicationFactory` tests on a throwaway DB per test. Validation exceeds the spec (year range + ISBN format checks beyond the required title/author).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
