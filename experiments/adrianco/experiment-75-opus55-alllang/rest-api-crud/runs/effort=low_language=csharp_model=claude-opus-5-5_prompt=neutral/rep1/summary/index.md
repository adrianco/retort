# Summary: effort=low language=csharp model=claude-opus-5-5 prompt=neutral · rep 1

- **Shape:** ASP.NET Core (.NET 10) minimal-API CRUD service backed by SQLite (`Microsoft.Data.Sqlite`).
- **Structure:** 1 source module (`Program.cs`) + 1 test module, wired via a `.slnx` solution.
- **Interfaces:** 6 HTTP routes (health + 5 CRUD), 1 `books` table, `BookRepository` with 5 methods.
- **Notable:** Very compact — the whole service (routing, records, validation, repository) lives in a single 125-line `Program.cs`; parameterised SQL, case-insensitive author filter, and a shared in-memory-SQLite trick for hermetic tests stand out.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
