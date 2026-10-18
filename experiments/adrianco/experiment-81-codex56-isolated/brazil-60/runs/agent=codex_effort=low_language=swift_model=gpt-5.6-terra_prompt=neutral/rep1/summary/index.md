# Summary: agent=codex effort=low language=swift model=gpt-5.6-terra prompt=neutral · rep 1

- **Shape:** Dependency-free Swift MCP server (hand-rolled JSON-RPC over stdio) over in-memory CSV data.
- **Structure:** 4 source modules + 1 test file (266 LOC total), zero external dependencies.
- **Interfaces:** 6 MCP tools (search_matches, team_statistics, head_to_head, search_players, standings, data_summary); no HTTP/CLI.
- **Notable:** Very dense single-line style; eager full load of all six CSVs; substring name matching with an accent/suffix/alias normalizer that misses the Athletico↔Atletico spelling split.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
