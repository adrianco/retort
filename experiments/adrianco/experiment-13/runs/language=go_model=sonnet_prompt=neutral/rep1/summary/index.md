# Summary: language=go_model=sonnet_prompt=neutral · rep 1

- **Shape:** Go MCP server (JSON-RPC 2.0 over stdio), pure standard library, in-memory CSV-backed query engine for Brazilian soccer data.
- **Structure:** 3 source modules (main.go, tools.go, data.go) + 1 test file; 0 third-party dependencies (no go.sum).
- **Interfaces:** 5 MCP methods + 7 tools (`search_matches`, `get_team_stats`, `get_standings`, `get_biggest_wins`, `search_players`, `get_competition_stats`, `list_teams`); no HTTP/CLI surface.
- **Notable:** Hand-rolled MCP protocol layer (no SDK); strong data-normalization handling for accents, state suffixes, and multiple date formats; loads all 6 datasets with exact-duplicate match dedup; 25 tests run against the real CSVs including a 20-question coverage test.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
