# Summary: language=typescript_model=sonnet-5_prompt=tdd · rep1

- **Shape:** TypeScript MCP server (stdio) over 6 in-memory Brazilian-soccer CSV datasets, using the `@modelcontextprotocol/sdk` McpServer + Zod, layered into parsing / normalization / query modules.
- **Structure:** 13 source modules, 12 test files (~96 test cases via vitest).
- **Interfaces:** 0 HTTP routes, 8 MCP tools (search_matches, team_record, compare_teams, search_players, competition_standings, dataset_statistics, player_club_context, list_team_competitions), 1 CLI entry (stdio), plus a wide exported library API.
- **Notable:** Dedicated cross-dataset deduplication (`canonicalMatches`) and a scored team-name canonicalization pass (accent/state-suffix handling with variant-count thresholds); custom quote-aware CSV parser and multi-format date parser rather than external libraries; tools return plain text; deduplication is recomputed on every query call rather than cached.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
