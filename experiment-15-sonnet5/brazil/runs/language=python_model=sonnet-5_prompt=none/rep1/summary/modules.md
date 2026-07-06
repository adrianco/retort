# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| soccer_mcp/__init__.py | Empty package marker | (none) |
| soccer_mcp/server.py | FastMCP server exposing repository queries as MCP tools | `mcp`, `main()`, `get_repository()`, 12 `@mcp.tool()` functions |
| soccer_mcp/repository.py | In-memory query engine over matches/players keyed on normalized team names | `SoccerRepository`, `TeamRecord` |
| soccer_mcp/data_loader.py | Loads six CSV datasets into unified Match/Player records, dedupes overlapping sources | `load_all()`, `SoccerData`, `load_*` loaders |
| soccer_mcp/models.py | Dataclasses for unified match and player records | `Match`, `Player` |
| soccer_mcp/team_names.py | Team name normalization to canonical keys + display names | `normalize_team()`, `teams_match()`, `strip_accents()` |
| tests/__init__.py | Empty test package marker | (none) |
| tests/conftest.py | Session-scoped `repo` fixture loading all real data | `repo` fixture |
| tests/test_data_loader.py | Data loading and dedupe tests | 8 test functions |
| tests/test_repository.py | Repository query/aggregation tests | 17 test functions |
| tests/test_server.py | MCP tool wrapper tests | 7 test functions |
| tests/test_team_names.py | Team name normalization tests | 8 test functions |
