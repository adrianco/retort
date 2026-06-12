# Summary: language=java · model=sonnet · prompt=neutral · rep 1

- **Shape:** Java 17 MCP server (stdio JSON-RPC, Jackson + OpenCSV) over in-memory Brazilian-soccer datasets.
- **Structure:** 7 main modules + 5 test files (61 `@Test` methods, 0 skipped).
- **Interfaces:** 9 MCP tools (5 match/team, 4 player); no HTTP/CLI surface; 6 CSVs loaded into memory.
- **Notable:** Clean layering (data / tools / server); team-name normalization handles state suffixes + accents; standings and stats computed from match results, not hardcoded.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
