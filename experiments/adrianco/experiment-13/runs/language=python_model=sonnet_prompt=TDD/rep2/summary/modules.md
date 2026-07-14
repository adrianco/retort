# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| data_loader.py | CSV loading + team-name/date normalization for all 6 datasets | `DataLoader`, `normalize_team_name()`, `teams_match()`, `parse_date()` |
| query_engine.py | Query/aggregation logic over the combined match + player data | `QueryEngine` (`find_matches`, `head_to_head`, `get_team_stats`, `find_players`, `get_standings`, `get_biggest_wins`, `competition_averages`) |
| server.py | FastMCP server wiring the engine to 7 MCP tools | `mcp`, the 7 `@mcp.tool()` functions |
| tests/test_data_loader.py | Normalization, date-parse and per-CSV loader tests | 18 test functions |
| tests/test_query_engine.py | Query-engine behavior tests over fixture DataFrames | 24 test functions |
| tests/test_server.py | MCP tool-registration tests | 3 test functions |
