# Summary: effort=low_language=csharp_model=claude-opus-5-5_prompt=neutral · rep 1

- **Shape:** C# / ASP.NET Core minimal-API CRUD service (.NET 10) with `Microsoft.Data.Sqlite` persistence.
- **Structure:** 3 source modules + 1 config file, 1 test file (11 test methods; 16 effective cases).
- **Interfaces:** 6 HTTP routes (5 CRUD + /health); `BookRepository` (6 methods) and `BookInput.Validate()`.
- **Notable:** Parameterized SQL throughout; `RETURNING id` on insert; connection-per-op repository; middleware converts malformed JSON to `400 {error}`; tests use `WebApplicationFactory` against a per-test throwaway SQLite file and include a cross-instance persistence check.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
