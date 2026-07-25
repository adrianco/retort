# Summary: language=csharp model=claude-opus-5 prompt=neutral · rep 1

- **Shape:** ASP.NET Core minimal-API CRUD service with EF Core + SQLite (.NET 10)
- **Structure:** 8 source modules, 4 test files (29 Fact/Theory → 49 cases)
- **Interfaces:** 6 HTTP routes (5 CRUD on /books + /health), 0 CLI, 0 exported library API
- **Notable:** strongly-typed `TypedResults` unions, RFC 7807 ProblemDetails, real DB-probing health check, ISBN-10/13 checksum validation with unique index + race-safe conflict handling, LIKE-wildcard escaping on the author filter — the most thorough approach among the small-task grid

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
