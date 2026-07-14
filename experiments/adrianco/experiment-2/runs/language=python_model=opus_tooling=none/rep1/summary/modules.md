# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| `brazilian_soccer/__init__.py` | Package initialization, export SoccerData | `SoccerData` |
| `brazilian_soccer/server.py` | MCP (Model Context Protocol) FastMCP server with 7 tools for querying soccer data | `mcp`, `FastMCP("brazilian-soccer")`, `main()`, tools: `find_matches`, `head_to_head`, `team_stats`, `standings`, `biggest_wins`, `average_goals`, `search_players` |
| `brazilian_soccer/data.py` | Data loading and query layer; loads 6 CSV datasets, normalizes team names, executes queries | `SoccerData`, `normalize_team()`, `_parse_date()`, `_strip_accents()`, `get_data()` |
| `tests/test_data.py` | 19 test cases covering team normalization, data loading, match queries, head-to-head, team stats, standings, aggregates, and player search | 19 test functions across 8 test classes |
