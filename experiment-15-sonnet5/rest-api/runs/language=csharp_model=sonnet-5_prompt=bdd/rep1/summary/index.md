# Summary: language=csharp_model=sonnet-5_prompt=bdd · rep 1

- **Shape:** ASP.NET Core (.NET 10) Web API with EF Core over SQLite, controller-based CRUD.
- **Structure:** 6 source modules + 3 test files (clean layered split: Controllers / Models / Dtos / Data).
- **Interfaces:** 7 HTTP routes (6 book CRUD + filter, 1 health), 1 EF-Core table.
- **Notable:** Idiomatic layered ASP.NET Core with DTO/entity separation and DataAnnotations validation; BDD `Given_..._When_..._Then_...` integration tests via `WebApplicationFactory` over a shared in-memory SQLite connection (11 passing cases, no skips). Unused `Microsoft.EntityFrameworkCore.InMemory` package reference in the API project.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
