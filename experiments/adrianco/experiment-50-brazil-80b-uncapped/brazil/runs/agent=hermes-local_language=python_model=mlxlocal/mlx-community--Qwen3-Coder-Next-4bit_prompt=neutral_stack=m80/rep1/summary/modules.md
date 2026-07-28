# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/models.py | Dataclasses for domain entities with `to_dict()` serializers | `Match`, `Player`, `TeamStats`, `TeamComparison`, `CompetitionStandings`, `BigWin`, `QueryResponse` |
| src/data_utils.py | CSV loading, team-name/date normalization, and all query logic | `DataUtils`, `DataLoader`, `QueryEngine`, `safe_int()` |
| src/mcp_server.py | FastMCP server exposing 12 query tools over stdio/SSE | `mcp`, `get_query_engine()`, `main()` |
| src/api.py | FastAPI app mirroring the query engine over HTTP | `app`, request models |
| src/main.py | Uvicorn launcher for the FastAPI app | `main()` |
| src/__init__.py | Package marker | (empty) |
| tests/conftest.py | Pytest fixtures for sample domain objects | `sample_match`, `sample_player`, `sample_team_stats`, `sample_competition_standings` |
| tests/test_api.py | Unit tests for models, DataUtils, QueryEngine, data loading, sample questions | 41 test functions across 7 classes |
| tests/test_mcp.py | Tests exercising each registered MCP tool via `mcp.call_tool` | 13 test functions in `TestMCPServer` |
