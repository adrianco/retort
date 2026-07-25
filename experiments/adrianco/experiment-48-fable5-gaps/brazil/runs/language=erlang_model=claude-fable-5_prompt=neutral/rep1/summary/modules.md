# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/bsmcp.erl | Escript entry point, delegates to the server | `main/1` |
| src/bsmcp_server.erl | MCP stdio transport: newline-delimited JSON-RPC on stdin/stdout | `main/1`, `run/1`, `handle_line/1` |
| src/bsmcp_rpc.erl | JSON-RPC 2.0 dispatch (initialize, ping, tools/list, tools/call) | `handle/1`, `parse_error_reply/0` |
| src/bsmcp_tools.erl | MCP tool schemas + dispatch onto the query layer | `tools/0`, `call/2` |
| src/bsmcp_query.erl | Search, filter, statistics over loaded data; team-name resolution | `find_team/1`, `search_matches/1`, `head_to_head/2`, `team_stats/2`, `standings/2`, `league_stats/1`, `biggest_wins/1`, `search_players/1`, `data_summary/0`, `match_date_sort_desc/1` |
| src/bsmcp_data.erl | Loads six Kaggle CSVs into ETS via a long-lived holder process; de-duplicates matches | `ensure_loaded/0`, `load/1`, `stop/0`, `default_dir/0`, `matches/0`, `players/0`, `teams/0`, `team_display/1`, `summary/0` |
| src/bsmcp_names.erl | Team/text normalization, competition canonicalization, date parsing | `norm_text/1`, `canonical/1`, `strip_geo/1`, `same_team/2`, `competition/1`, `parse_date/1`, `format_date/1` |
| src/bsmcp_csv.erl | RFC-4180-style CSV parser (quotes, escapes, CR/LF, BOM) | `parse_file/1`, `parse_binary/1` |
| src/bsmcp_format.erl | Renders query results as human-readable UTF-8 text | `matches/2`, `team_stats/1`, `standings/2`, `players/2`, `league_stats/1`, `biggest_wins/2`, `data_summary/1`, `match_line/1` |
| src/bsmcp.app.src | OTP application resource file | application `bsmcp` |
| test/bsmcp_csv_tests.erl | EUnit tests for the CSV parser | 9 test functions |
| test/bsmcp_names_tests.erl | EUnit tests for name/date/competition normalization | 13 test functions |
| test/bsmcp_query_tests.erl | EUnit generator test over the query layer with a synthetic dataset | `query_test_/0` |
| test/bsmcp_mcp_tests.erl | EUnit generator test exercising the JSON-RPC/MCP handshake and tools | `mcp_test_/0` |
