# Summary: effort=low_language=java_model=claude-haiku-5-5_prompt=neutral · rep 2

- **Shape:** Java 21 stdio MCP server (JSON-RPC 2.0) over Jackson, with in-memory CSV-backed query engine for Brazilian soccer data.
- **Structure:** 11 main modules, 6 test files (40 `@Test` methods), 1 shared test-fixtures helper.
- **Interfaces:** 7 MCP tools (search_matches, team_record, head_to_head, search_players, competition_standings, league_stats, rank_teams); all 6 Kaggle CSVs loaded and de-duplicated.
- **Notable:** Dedicated `TeamNames` normalization layer (accents, state suffixes, aliases) to unify names across sources; cross-source fixture de-duplication; real-dataset tests (2019 Brasileirão champion, performance). Queries are linear in-memory scans.

See [modules.md](modules.md), [interfaces.md](interfaces.md), [flow.md](flow.md).
