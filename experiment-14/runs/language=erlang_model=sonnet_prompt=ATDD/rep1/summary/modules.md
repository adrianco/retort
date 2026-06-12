# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/soccer_mcp.erl | escript entry point + MCP JSON-RPC 2.0 protocol handler (stdin/stdout loop) | `main/1`, `handle_message/1` |
| src/soccer_tools.erl | MCP tool definitions and `tools/call` dispatch to data queries | `list/0`, `call/2` |
| src/soccer_data.erl | CSV loading into persistent_term + all query/aggregation logic | `init/0`, `find_matches_all/1`, `find_players_all/1`, `get_head_to_head/3`, `get_standings/2`, `compute_team_stats/2`, `stats_biggest_wins/1`, `stats_avg_goals/1` |
| src/soccer_csv.erl | Hand-written CSV parser (quoted fields, BOM strip, CRLF/LF) | `parse_file/1` |
| src/soccer_mcp.app.src | OTP application resource file | `soccer_mcp` app |
| test/soccer_mcp_SUITE.erl | Common Test acceptance suite, 15 cases exercising the MCP protocol | `all/0`, `ac01..ac15` |
