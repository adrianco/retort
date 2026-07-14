# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| data_loader.py | Loads and normalizes all 6 Kaggle CSVs into DataFrames + unified match/player lists; runs query/aggregation methods | `MatchDataset`, `normalize_team_name()`, `parse_iso_date()`, `parse_brazilian_date()` |
| knowledge_graph.py | Builds a NetworkX MultiDiGraph of teams/matches/competitions/seasons/players and runs graph traversals | `KnowledgeGraph` |
| models.py | Pydantic request/response models for the MCP tools | `MatchSearchRequest`, `TeamStatsRequest`, `HeadToHeadRequest`, `PlayerSearchRequest`, `SeasonStandingsRequest`, `MatchResponse`, `PlayerResponse`, `MCPResponse`, plus 10 more |
| server.py | MCP server exposing 11 soccer-data tools; loads data and graph on startup | `app`, `initialize()`, `main()`, 11 `@app.tool()` functions |
| tests/test_data_loader.py | Unit tests for loader, normalization, and query methods | 49 test functions |
| tests/test_queries.py | Tests for query/aggregation behavior | 29 test functions |
| tests/test_knowledge_graph.py | Tests for graph construction and traversal | 15 test functions |
| tests/__init__.py | Empty package marker | (none) |
| requirements.txt | Dependencies: pandas, pydantic, networkx, mcp, pytest, pytest-asyncio | (none) |
