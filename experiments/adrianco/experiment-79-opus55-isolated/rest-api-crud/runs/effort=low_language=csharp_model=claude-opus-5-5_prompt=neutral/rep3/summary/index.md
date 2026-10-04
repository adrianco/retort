# Summary: effort=low_language=csharp_model=claude-opus-5-5_prompt=neutral · rep 3

- **Shape:** C# / ASP.NET Core minimal-API CRUD service backed by SQLite (`Microsoft.Data.Sqlite`).
- **Structure:** 3 source modules + 1 test file (9 test methods, 12 cases).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), 1 SQLite table, `BookRepository` library API.
- **Notable:** Idiomatic minimal-API style; parameterized SQL with `RETURNING id`; connection-per-operation; problem-details validation responses; tests use `WebApplicationFactory` against a throwaway per-test SQLite file.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
