# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer_mcp/server.py | MCP server (FastMCP); registers 14 tools over stdio | `mcp`, `main()`, `search_matches`, `get_head_to_head`, `get_team_record`, `compare_teams`, `get_standings`, `get_champion`, `search_players`, … |
| brazilian_soccer_mcp/queries.py | Query layer: match search, team records, head-to-head, standings, champions, player search, statistics | `QueryEngine`, `resolve_competition()` |
| brazilian_soccer_mcp/data_loader.py | Loads the 6 Kaggle CSVs into unified `matches`/`players` DataFrames on a common schema | `load_all()`, `load_matches()`, `load_players()`, `SoccerData` |
| brazilian_soccer_mcp/graph.py | Knowledge graph: team/player indices, name resolution over the DataFrames | `KnowledgeGraph`, `TeamNode`, `TeamNotFoundError` |
| brazilian_soccer_mcp/normalize.py | Team-name normalization (accents, state suffixes), date/goal parsing | `normalize_key()`, `parse_datetime()`, `strip_accents()`, `disambiguate_key()` |
| brazilian_soccer_mcp/formatting.py | Turns query results (DataFrames/dicts) into human-readable tool responses | `format_matches()`, `format_head_to_head()`, `format_standings()`, `format_champion()`, … |
| brazilian_soccer_mcp/__init__.py | Package marker | — |
| tests/conftest.py | Session-scoped BDD fixtures loading the full dataset once | `soccer_data`, `graph`, `engine` fixtures |
| tests/test_queries.py | BDD specs for QueryEngine | 32 test functions |
| tests/test_normalize.py | BDD specs for name/date normalization | 18 test functions |
| tests/test_server.py | BDD specs for the MCP tool wrappers | 12 test functions |
| tests/test_data_loader.py | BDD specs for CSV loading + unified schema | 11 test functions |
| tests/test_graph.py | BDD specs for the knowledge graph | 7 test functions |
| tests/test_performance.py | Query latency budget checks | 5 test functions |
