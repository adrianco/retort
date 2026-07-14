# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer_mcp/__init__.py | Package init | (empty) |
| brazilian_soccer_mcp/data_loader.py | Loads/caches the 6 Kaggle CSVs, normalizes team names & dates | `DataLoader`, `normalize_team_name()`, `parse_brazilian_date()`, `load_*()` loaders |
| brazilian_soccer_mcp/query_handlers.py | Query logic for all 5 capability categories | `find_matches()`, `get_team_statistics()`, `get_head_to_head()`, `search_players()`, `get_standings()`, `get_biggest_wins()`, `get_average_goals()`, `get_best_away_record()`, `get_brazilian_players_by_club()`, `get_team_names()` |
| brazilian_soccer_mcp/server.py | FastMCP server registering 11 MCP tools | `mcp`, `search_matches`, `get_team_stats`, `get_head_to_head`, `search_players`, `get_standings`, `get_biggest_wins`, `get_average_goals`, `get_best_away_record`, `get_brazilian_players_by_club`, `list_teams`, `list_competitions` |
| tests/__init__.py | Test package init | (empty) |
| tests/test_brazilian_soccer.py | Pytest suite: 121 tests across 23 classes | 23 `Test*` classes |
