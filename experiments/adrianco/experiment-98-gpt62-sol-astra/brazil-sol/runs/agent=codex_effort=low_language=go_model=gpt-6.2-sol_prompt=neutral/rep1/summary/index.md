# Summary: agent=codex effort=low language=go model=gpt-6.2-sol prompt=neutral · rep 1

- **Shape:** Go stdlib JSON-RPC 2.0 MCP server over stdio, in-memory store backed by six Kaggle CSVs.
- **Structure:** 5 source modules + 1 test file (~1,595 LoC), zero external dependencies.
- **Interfaces:** 4 MCP methods / 6 MCP tools (search_matches, team_stats, search_players, competition_standings, analyze_matches, club_profile).
- **Notable:** Cross-source fixture reconciliation (dedup + field merge + final-stage tagging), accent/alias-insensitive name normalization, nullable-goal model for unscored fixtures, standings computed with completeness flag. Strongly-typed, generics-based tool/pagination helpers.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
