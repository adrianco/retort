# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/soccer.h | Shared types (json_t, db_t, match_t, player_t, sb_t) and all prototypes | `db_load`, `mcp_handle`, `q_*` |
| src/data.c | CSV loading, UTF-8/team-name/date normalization, cross-file de-duplication, string builder | `db_load`, `team_key`, `norm_date`, `comp_canon`, `sb_printf` |
| src/query.c | The 12 query implementations (all emit human-readable text) | `q_search_matches`, `q_head_to_head`, `q_team_stats`, `q_standings`, `q_search_players`, `q_club_summary`, `q_biggest_wins`, `q_competition_stats`, `q_best_records`, `q_team_competitions`, `q_derbies`, `q_compare_seasons` |
| src/mcp.c | JSON parser + JSON-RPC 2.0 / MCP protocol (initialize, tools/list, tools/call), tool registry + dispatch | `json_parse`, `mcp_handle`, `mcp_call_tool` |
| src/main.c | Entry point: loads data dir (arg or `SOCCER_DATA_DIR`), reads JSON-RPC lines from stdin | `main` |
| tests/test_soccer.c | BDD-style test harness driving queries + MCP protocol against real CSVs | `main` (9 scenario groups) |
