# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | MCP server (FastMCP) registering 9 query tools over stdio | `mcp`, `search_matches`, `get_team_stats`, `head_to_head`, `get_competition_standings`, `search_players`, `top_scoring_teams`, `biggest_wins`, `aggregate_stats`, `best_home_records` |
| query_tools.py | Pure query/aggregation functions over the loaded DataFrames | `search_matches`, `get_team_stats`, `head_to_head`, `get_competition_standings`, `search_players`, `top_scorers_by_team`, `biggest_wins`, `aggregate_stats`, `best_home_records` |
| data_loader.py | Loads the 6 Kaggle CSVs, normalizes team names/dates, caches a singleton | `SoccerData`, `normalize_team()`, `get_data()`, `DATA_DIR` |
| test_server.py | pytest suite exercising loading, normalization, and every query tool | 52 test functions across 11 classes |
