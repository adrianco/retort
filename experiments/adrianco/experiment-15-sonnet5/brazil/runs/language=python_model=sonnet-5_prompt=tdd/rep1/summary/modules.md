# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer_mcp/__init__.py | Package marker (empty) | — |
| brazilian_soccer_mcp/normalize.py | Team-name canonicalization (accents/state-suffix/alias) + multi-format date parsing | `canonical_team_key()`, `display_team_name()`, `parse_date()` |
| brazilian_soccer_mcp/data_loader.py | Loads/unifies 5 match CSVs + FIFA players into cached DataFrames | `load_matches()`, `load_players()`, `MATCH_COLUMNS` |
| brazilian_soccer_mcp/queries.py | Query/aggregation logic over the match & player frames | `find_matches()`, `head_to_head()`, `team_record()`, `standings()`, `biggest_wins()`, `average_goals_per_match()`, `home_win_rate()`, `search_players()`, `top_players()` |
| brazilian_soccer_mcp/server.py | FastMCP server exposing 9 tools; formats results as text | `mcp`, 9 `@mcp.tool()` handlers |
| tests/test_normalize.py | Unit tests for name/date normalization | 13 test functions |
| tests/test_data_loader.py | Unit tests for CSV loading/unification | 11 test functions |
| tests/test_queries.py | Unit tests for query/aggregation logic (fixtures) | 14 test functions |
| tests/test_server.py | Async tests exercising the MCP tools | 11 test functions |
