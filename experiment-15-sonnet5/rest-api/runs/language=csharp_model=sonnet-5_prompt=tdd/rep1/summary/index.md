# Summary: language=csharp · model=sonnet-5 · prompt=tdd · rep 1

- **Shape:** ASP.NET Core minimal API (.NET 10) with EF Core + SQLite persistence.
- **Structure:** 3 source modules + 4 test files (14 integration tests via `WebApplicationFactory`).
- **Interfaces:** 6 HTTP routes (health + 5-verb book CRUD), 1 `Books` table, 1 shared request DTO.
- **Notable:** Validation refactored into a shared `BookCreateRequest.IsValid` reused by POST and PUT. A dedicated `AppStartupTests` regression test reproduces and guards against a real bug — the production `Program.cs` had not created the SQLite schema at startup (masked in tests by `EnsureCreated`); the agent surfaced it via a live run and fixed it with `db.Database.EnsureCreated()`.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
