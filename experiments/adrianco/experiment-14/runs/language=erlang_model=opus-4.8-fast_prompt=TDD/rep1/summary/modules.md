# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/bsmcp.erl | escript entry point | `main/1` |
| src/bsmcp_server.erl | stdio transport: read/serve loop over stdin, NDJSON I/O | `main/1`, `run/1`, `load_store/1`, `process_line/2` |
| src/bsmcp_mcp.erl | JSON-RPC 2.0 request handling + JSON codec | `handle_request/2`, `encode/1`, `decode/1` |
| src/bsmcp_tools.erl | MCP tool catalog + dispatch to query layer | `list/0`, `call/3` |
| src/bsmcp_query.erl | Query/aggregation over matches & players | `find_matches/2`, `head_to_head/3`, `team_record/3`, `find_players/2`, `top_players/3`, `standings/3`, `avg_goals/1`, `home_win_rate/1`, `biggest_wins/2` |
| src/bsmcp_data.erl | Dataset loading + per-CSV row → canonical map | `load_matches/1`, `load_players/1`, `parse_date/1`, `parse_int/1`, `dedup/1`, `*_row/1` |
| src/bsmcp_csv.erl | Minimal RFC-4180 CSV parser | `parse/1`, `parse_to_maps/1`, `parse_file/1`, `parse_file_to_maps/1` |
| src/bsmcp_normalize.erl | Team-name normalization (suffix/accent handling) | `normalize/1`, `display_name/1`, `same_team/2` |
| src/bsmcp_aliases.erl | Canonical team aliases | `lookup/1` |
| src/bsmcp_format.erl | Human-readable UTF-8 result formatting | `match_line/1`, `matches/1`, `team_record/2`, `head_to_head/4`, `players/1`, `standings/3` |
| src/bsmcp.app.src | OTP application resource file | — |
| test/bsmcp_csv_tests.erl | CSV parser tests | 11 test functions |
| test/bsmcp_data_tests.erl | Row-transform / loading tests | 15 test functions |
| test/bsmcp_normalize_tests.erl | Name-normalization tests | 17 test functions |
| test/bsmcp_format_tests.erl | Formatting tests | 10 test functions |
| test/bsmcp_query_tests.erl | Match/player query tests | 12 test functions |
| test/bsmcp_query2_tests.erl | Standings/stats/record query tests | 14 test functions |
| test/bsmcp_tools_tests.erl | Tool dispatch tests | 11 test functions |
| test/bsmcp_mcp_tests.erl | JSON-RPC handler/codec tests | 12 test functions |
| test/bsmcp_server_tests.erl | stdio transport tests | 5 test functions |
