# Summary: effort=low language=swift model=claude-haiku-5-5 prompt=neutral · rep 3

- **Shape:** Swift Package (SwiftPM) MCP stdio server over JSON-RPC 2.0, with a pure-Foundation in-memory query engine over Kaggle CSVs. No external dependencies.
- **Structure:** 13 source modules (SoccerCore library + soccer-mcp executable), 7 test files (57 test functions).
- **Interfaces:** 5 JSON-RPC methods + 9 MCP tools (search_matches, team_record, head_to_head, standings, search_players, biggest_wins, league_stats, rank_teams, ask).
- **Notable:** Clean library/executable split; NL `ask` tool routes to the typed tools; DataLoaderTests run against the real 16.7k-match / 18k-player dataset, not just fixtures; season-level dedupe handles overlapping source files.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
