# Summary: effort=low_language=csharp_model=claude-opus-5-5_prompt=neutral · rep 2

- **Shape:** ASP.NET Core Minimal API (C#/.NET 10) CRUD over SQLite via `Microsoft.Data.Sqlite`.
- **Structure:** 1 source module (`Program.cs`) + 1 test file (6 integration `[Fact]`s).
- **Interfaces:** 6 HTTP routes (5 CRUD + health); 1 SQLite table; `BookRepository` with 5 methods.
- **Notable:** Extremely compact — the whole service is 127 lines in one file using records, collection expressions, and top-level statements. Tests use `WebApplicationFactory` with a per-test shared in-memory SQLite DB.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
