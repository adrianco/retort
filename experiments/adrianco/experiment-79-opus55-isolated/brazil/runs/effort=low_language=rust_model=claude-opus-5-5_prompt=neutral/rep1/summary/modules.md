# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/lib.rs | Crate root; re-exports data types and declares the four modules | `data`, `mcp`, `normalize`, `queries` |
| src/main.rs | CLI entry: serve MCP on stdio, `call TOOL JSON`, or `tools` | `main()`, `run()` |
| src/data.rs | In-memory DB built from the six Kaggle CSVs; team-name merge + primary-source de-dup | `Database`, `Database::load`, `Match`, `Player`, `Competition`, `Source`, `find_data_dir()` |
| src/normalize.rs | Team-name canonicalisation, accent folding, multi-format date parsing, derby table | `canonical()`, `fold()`, `parse_date()`, `is_known_club()`, `DERBIES` |
| src/queries.rs | Query layer: match/team/player/competition/statistics answers as formatted text | `Database::{search_matches, head_to_head, team_stats, team_profile, standings, competition_summary, league_stats, biggest_wins, team_rankings, compare_seasons, derbies, search_players, player_details, brazilian_clubs_players, list_teams, dataset_info}`, `MatchFilter`, `PlayerFilter`, `Record`, `Venue` |
| src/mcp.rs | JSON-RPC 2.0 MCP server over stdio: tool schemas, dispatch, error mapping | `serve()`, `handle_message()`, `call_tool()`, `tool_definitions()`, `TOOLS` |
| tests/bdd.rs | Behaviour-driven scenarios over the real CSVs | 39 `#[test]` functions |
