# Summary: language=java model=sonnet prompt=TDD · rep 1

- **Shape:** Java 17 MCP stdio server (official `io.modelcontextprotocol.sdk`) over in-memory CSV data, parsed with OpenCSV.
- **Structure:** 9 main modules + 6 JUnit 5 test files (~794 main LOC, ~213 test LOC).
- **Interfaces:** 6 MCP tools (find_matches, get_team_stats, find_players, get_head_to_head, get_standings, get_biggest_wins); ~20 exported service methods.
- **Notable:** Clean layering (loader → model → service → server); `TeamNameNormalizer` handles the `-SP` suffix problem from the spec. Tests cover the service/loader layer thoroughly but not the MCP handler layer. Date filtering is season-only.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
