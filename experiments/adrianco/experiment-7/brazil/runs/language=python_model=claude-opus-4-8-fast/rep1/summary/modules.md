# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer_mcp/server.py | FastMCP server; registers query tools as MCP tools | `mcp`, `main()`, 13 `@mcp.tool` functions |
| brazilian_soccer_mcp/knowledge_graph.py | Query engine over normalised match/player tables | `KnowledgeGraph`, `get_knowledge_graph()` |
| brazilian_soccer_mcp/data_loader.py | Reads the 6 Kaggle CSVs into tidy DataFrames | `load_all()`, `load_matches()`, `load_players()` |
| brazilian_soccer_mcp/normalize.py | Team-name / accent / date normalisation | `canonical_norm()`, `canonical_team_name()`, `parse_date()`, `team_matches()` |
| brazilian_soccer_mcp/formatting.py | Renders query results to text answers | `format_matches()`, `format_team_record()`, `format_players()`, `format_standings()`, … |
| brazilian_soccer_mcp/__init__.py | Package marker | — |
| run_server.py | Convenience launcher (`python run_server.py`) | `__main__` |
| tests/conftest.py | Shared pytest fixtures (knowledge graph) | fixtures |
| tests/test_match_queries.py | Match-query BDD scenarios | 6 test functions |
| tests/test_team_queries.py | Team record / H2H scenarios | 6 test functions |
| tests/test_player_queries.py | Player search scenarios | 7 test functions |
| tests/test_competition_queries.py | Standings / champion / relegation | 5 test functions |
| tests/test_statistics.py | Aggregate statistics scenarios | 6 test functions |
| tests/test_server_tools.py | MCP tool registration + 20-question coverage | 4 test functions |
| tests/test_data_loading.py | Data-loading & normalisation | 10 test functions |
| features/brazilian_soccer.feature | Gherkin spec mirrored by the pytest suite | — |
