# Summary: language=typescript · model=opus-4.8-fast · prompt=ATDD · rep 1

- **Shape:** TypeScript MCP server (`@modelcontextprotocol/sdk`) over an in-memory store, querying bundled Kaggle Brazilian-soccer CSVs; zod-validated tools, stdio transport.
- **Structure:** 6 source modules (clean domain / data / server layering), 8 test files (6 acceptance + 2 unit), 34 tests.
- **Interfaces:** 7 MCP tools (find_matches, head_to_head, team_record, find_players, competition_standings, competition_statistics, dataset_summary); 1 CLI entry point; no HTTP.
- **Notable:** Exemplary ATDD execution — acceptance tests drive the system *only* through the real MCP client/server protocol via an in-memory transport, each from a fresh empty store. Sophisticated data normalization (suffix/accent/alias handling, ambiguity-aware state disambiguation, cross-file fixture de-dup).

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
