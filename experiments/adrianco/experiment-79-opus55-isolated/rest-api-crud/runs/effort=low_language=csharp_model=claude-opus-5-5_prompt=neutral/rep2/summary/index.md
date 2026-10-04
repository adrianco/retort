# Summary: effort=low_language=csharp_model=claude-opus-5-5_prompt=neutral · rep 2

- **Shape:** ASP.NET Core Minimal API with Microsoft.Data.Sqlite persistence (.NET 10).
- **Structure:** 3 source modules + 1 test file (353 LOC total, source only).
- **Interfaces:** 6 HTTP routes (5 CRUD + /health), 5 `BookStore` methods, SQLite `books` table.
- **Notable:** Idiomatic minimal-API style — `RETURNING` clauses for create/update, parameterized SQL, `COLLATE NOCASE` author filter, route constraint `{id:long}`. Tests use `WebApplicationFactory<Program>` against a throwaway temp SQLite file with pool cleanup on dispose.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
