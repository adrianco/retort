# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer_mcp/__init__.py | Package marker | (none) |
| brazilian_soccer_mcp/data_loader.py | Load/normalize 6 Kaggle CSVs into a unified match DataFrame + FIFA players | `get_match_data()`, `get_player_data()`, `normalize_team_name()`, `parse_date()`, `parse_goals()`, `get_all_competitions()` |
| brazilian_soccer_mcp/query_engine.py | All query logic over matches/players | `QueryEngine` (`find_matches_by_team`, `find_matches_between_teams`, `get_team_statistics`, `get_standings`, `get_champion`, `search_player`, `get_players_by_nationality`, `get_players_by_club`, `get_average_goals_per_match`, `get_biggest_wins`, …) |
| brazilian_soccer_mcp/server.py | FastMCP server exposing 22 `@mcp.tool()` handlers | `mcp`, `main()` |
| tests/test_brazilian_soccer_mcp.py | Pytest suite (88 tests, 10 classes) | fixtures `match_data`, `player_data`, `engine`, `all_competitions` |
