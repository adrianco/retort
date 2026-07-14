# Summary: language=csharp · model=sonnet-4.6 · prompt=tdd · rep 1

- **Shape:** C# / .NET 10 MCP server (ModelContextProtocol 1.4.0 over stdio) with an in-memory CSV-backed query engine (CsvHelper).
- **Structure:** 9 server source files (4 tool classes, 3 services, 4 models) + 6 test files; ~1092 server LOC, ~384 test LOC.
- **Interfaces:** 15 MCP tools across match / team / player / statistics domains; no HTTP/CLI surface.
- **Notable:** Clean layering (Tools → DataRepository → CsvDataLoader/Normalizer). Fuzzy team matching via diacritic-stripping normalizer, with an explicit exact-match path for standings to avoid Atlético-MG/PR collapse. 45 integration-style tests pass against real Kaggle data. One leftover empty xUnit template test (`UnitTest1`).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
