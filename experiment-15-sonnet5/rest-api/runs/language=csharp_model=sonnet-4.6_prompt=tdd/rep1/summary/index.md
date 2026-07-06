# Summary: language=csharp_model=sonnet-4.6_prompt=tdd · rep 1

- **Shape:** ASP.NET Core 10 Web API (controller-based) with EF Core + SQLite persistence.
- **Structure:** 5 source modules + 1 test file (10 integration tests via `WebApplicationFactory`).
- **Interfaces:** 6 HTTP routes (full CRUD on `/books`, `?author=` filter, `/health`); 1 EF Core entity.
- **Notable:** Clean idiomatic C# — primary constructors, records for DTOs, attribute-based validation with automatic `400`. Tests share a per-instance in-memory SQLite connection to isolate the production SQLite provider. Test-first structure consistent with the TDD prompt.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
