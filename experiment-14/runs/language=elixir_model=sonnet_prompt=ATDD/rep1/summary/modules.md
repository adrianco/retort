# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/brazilian_soccer_mcp.ex | Top-level module + docs | `BrazilianSoccerMcp` |
| lib/brazilian_soccer_mcp/application.ex | OTP app; supervises DataStore | `start/2` |
| lib/brazilian_soccer_mcp/server.ex | MCP JSON-RPC 2.0 handler; tools/list, tools/call, initialize | `handle_request/1` |
| lib/brazilian_soccer_mcp/stdio_runner.ex | stdin/stdout JSON-RPC transport | `start/0` |
| lib/brazilian_soccer_mcp/data_store.ex | GenServer loading 6 CSVs into ETS; match/player query helpers | `query_matches/1`, `query_players/1`, `all_matches/1`, `all_players/0` |
| lib/brazilian_soccer_mcp/team_normalizer.ex | Normalizes team names (strip state suffix, accents) | `normalize/1`, `matches?/2` |
| lib/brazilian_soccer_mcp/tools.ex | Namespace marker | — |
| lib/brazilian_soccer_mcp/tools/find_matches.ex | `find_matches` tool + head-to-head summary | `call/1` |
| lib/brazilian_soccer_mcp/tools/get_team_stats.ex | `get_team_stats` tool (W/D/L, goals, win rate) | `call/1` |
| lib/brazilian_soccer_mcp/tools/find_players.ex | `find_players` tool (name/nationality/club/rating) | `call/1` |
| lib/brazilian_soccer_mcp/tools/get_competition_standings.ex | `get_competition_standings` tool (computed league table) | `call/1` |
| lib/brazilian_soccer_mcp/tools/get_statistics.ex | `get_statistics` tool (4 aggregate stat types) | `call/1` |
| test/acceptance/mcp_tools_test.exs | Acceptance suite through the MCP protocol | 27 tests |
| test/brazilian_soccer_mcp_test.exs | Smoke test (module loads) | 1 test |
| test/test_helper.exs | ExUnit bootstrap | — |
