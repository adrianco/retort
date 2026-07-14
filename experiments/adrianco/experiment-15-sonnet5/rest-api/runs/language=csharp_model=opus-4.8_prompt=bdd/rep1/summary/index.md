# Summary: language=csharp_model=opus-4.8_prompt=bdd · rep 1

- **Shape:** ASP.NET Core Minimal API (.NET 10) with EF Core + SQLite CRUD for a book collection.
- **Structure:** 3 source modules, 1 test file (8 BDD-style integration tests).
- **Interfaces:** 6 HTTP routes (5 CRUD + `/health`), 0 CLI commands, 3 exported types.
- **Notable:** Clean minimal-API idiom; integration tests boot the real app against an
  in-memory SQLite connection via `WebApplicationFactory<Program>`, giving isolated,
  file-free tests. Validation, 404 handling, and `?author=` filtering all present.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
