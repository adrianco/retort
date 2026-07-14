# Summary: language=csharp_model=sonnet-5_prompt=none · rep 1

- **Shape:** ASP.NET Core (.NET 10) minimal-API CRUD with EF Core + SQLite
- **Structure:** 4 source modules + 2 test modules, 1 test file (7 tests)
- **Interfaces:** 6 HTTP routes (5 CRUD + health), 1 SQLite table, 1 request DTO
- **Notable:** Clean layering (Models/Data/Program), DTO/entity separation, DataAnnotations validation shared by POST+PUT, integration tests use in-memory SQLite via `WebApplicationFactory`. `?author=` filter is case-sensitive (`Contains`), whereas the README claims case-insensitive.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
