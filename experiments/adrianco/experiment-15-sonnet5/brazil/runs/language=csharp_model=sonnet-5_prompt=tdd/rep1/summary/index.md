# Summary: language=csharp model=sonnet-5 prompt=tdd · rep 1

- **Shape:** C#/.NET MCP stdio server (Brazilian soccer knowledge graph) over CSV data, split into a `Core` library + `Server` host, using the `ModelContextProtocol` SDK and `Microsoft.Extensions.Hosting` DI.
- **Structure:** ~28 source files across Core (Data/Normalization/Queries) and Server, plus 16 test files (~73 xUnit tests).
- **Interfaces:** 15 MCP tools (13 distinct query tools) wrapping 5 query services; no HTTP/CLI; all data loaded in-memory from 6 CSV files.
- **Notable:** Layered design with a dedicated normalization layer (team-name key/display, diacritic folding, flexible date + competition parsing) and cross-dataset match deduplication with per-competition source priority; standings/champions computed from match results rather than stored.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
