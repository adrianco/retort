# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| lib/brazilian_soccer_mcp.ex | App escript entry; starts the stdio MCP loop | `main/1` |
| lib/brazilian_soccer_mcp/application.ex | OTP Application; supervises DataStore | `start/2` |
| lib/brazilian_soccer_mcp/mcp_server.ex | JSON-RPC 2.0 stdio server; initialize/tools.list/tools.call | `run/0` |
| lib/brazilian_soccer_mcp/tools.ex | MCP tool definitions (7 tools) + dispatch | `list_tools/0`, `call_tool/2` |
| lib/brazilian_soccer_mcp/query_engine.ex | Query logic for all tools; returns formatted strings | `search_matches/1`, `get_team_stats/1`, `head_to_head/1`, `search_players/1`, `get_standings/1`, `get_biggest_wins/1`, `get_summary_stats/1` |
| lib/brazilian_soccer_mcp/data_loader.ex | Parses the 6 Kaggle CSVs into match/player maps | `load_all/0`, `load_brasileirao/0`, … `load_players/0` |
| lib/brazilian_soccer_mcp/data_store.ex | GenServer holding all parsed data in memory | `start_link/1`, `get_all_matches/0`, `get_players/0`, … |
| lib/brazilian_soccer_mcp/team_normalizer.ex | Normalizes team names (state suffixes, accents, aliases) | `normalize/1`, `canonical/1`, `matches?/2` |
| test/brazilian_soccer_mcp_test.exs | ExUnit suite (50 tests across all modules) | 50 test functions |
| test/test_helper.exs | ExUnit bootstrap | `ExUnit.start/0` |
