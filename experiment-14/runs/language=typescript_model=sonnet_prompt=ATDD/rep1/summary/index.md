# Summary: language=typescript_model=sonnet_prompt=ATDD · rep 1

- **Shape:** TypeScript MCP server (`@modelcontextprotocol/sdk`, stdio transport) over seven Brazilian-soccer CSVs, read with `csv-parse`.
- **Structure:** 9 source modules + 1 acceptance test file; tools split one-per-file under `src/tools/`.
- **Interfaces:** 5 MCP tools (find_matches, get_team_stats, find_players, get_head_to_head, get_standings); no HTTP/CLI surface.
- **Notable:** ATDD-style acceptance suite drives the *real* server through the MCP client over stdio (no internal back-doors); a shared `teamsMatch` normalizer handles inconsistent team naming across datasets.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
