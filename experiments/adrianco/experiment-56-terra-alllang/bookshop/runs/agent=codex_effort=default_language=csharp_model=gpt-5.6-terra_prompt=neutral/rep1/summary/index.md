# Summary: agent=codex language=csharp model=gpt-5.6-terra prompt=neutral · rep 1

- **Shape:** ASP.NET Core minimal-API (net10.0) book CRUD over `Microsoft.Data.Sqlite` with a hand-written repository (no EF Core/ORM).
- **Structure:** 3 source modules (Program, BookRepository, Models) + config; 1 xUnit test file with 4 integration tests, in a 2-project solution.
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), `?author=` LIKE filter, RFC 7807 validation errors; `BookRepository` with 6 public async methods; 1 SQLite table.
- **Notable:** Clean, idiomatic minimal-API style — records for DTOs, primary-constructor repository, raw-string SQL with parameterized queries. Tests target the repository layer (not the HTTP endpoints) against real temp-file SQLite databases. Each call opens its own connection; no shared connection, transactions, or DB-error handling.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
