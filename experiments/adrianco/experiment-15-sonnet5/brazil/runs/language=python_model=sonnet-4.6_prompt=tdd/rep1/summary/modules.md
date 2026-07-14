# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| data_loader.py | Load the 6 Kaggle CSVs; normalize team names (strip state suffix) and parse ISO/Brazilian dates | `DataLoader`, `load_all()`, `all_match_dfs`, `normalize_team_name()`, `parse_date()` |
| query_engine.py | Query layer over the loaded DataFrames — match/player search, team stats, standings, aggregates | `QueryEngine`, `search_matches()`, `get_team_stats()`, `search_players()`, `get_head_to_head()`, `get_standings()`, `get_biggest_wins()`, `get_average_goals()`, `get_home_win_rate()`, `get_top_scoring_teams()` |
| server.py | FastMCP server exposing 7 MCP tools over the query engine | `create_server()`, tools: `search_matches`, `get_team_stats`, `search_players`, `get_head_to_head`, `get_standings`, `get_biggest_wins`, `get_statistics` |
| test_data_loader.py | Unit tests for loaders, normalization, date parsing | 22 test functions |
| test_query_engine.py | Tests for all query-engine methods | 42 test functions |
| test_server.py | Tests for server creation, tool registration, tool-call integration | 16 test functions |
| pyproject.toml | Project metadata + dependencies (mcp, pandas) | — |
