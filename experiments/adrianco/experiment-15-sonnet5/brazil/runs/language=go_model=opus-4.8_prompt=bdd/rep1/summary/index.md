# Summary: go · opus-4.8 · bdd · rep 1

- **Shape:** Go stdlib MCP server (JSON-RPC 2.0 over stdio) with an in-memory CSV-backed query engine for Brazilian soccer data.
- **Structure:** 10 source modules across `main` + `internal/mcp` + `internal/soccer`; 6 test files (44 test functions). Only external dependency is `golang.org/x/text` for accent folding.
- **Interfaces:** 7 MCP tools (search_matches, head_to_head, team_record, standings, search_players, match_statistics, data_overview); no HTTP routes; one `-data` CLI flag.
- **Notable:** Clean domain/transport separation (soccer package knows nothing about MCP); dedicated normalisation layer with an explicit club-alias table to disambiguate colliding base names (e.g. the three Atlético clubs); fixture deduplication with ±1-day matching to merge overlapping datasets; results returned as formatted plain text rather than structured JSON.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
