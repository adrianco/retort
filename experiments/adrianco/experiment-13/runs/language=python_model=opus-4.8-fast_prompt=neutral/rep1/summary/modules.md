# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| data_loader.py | Load + unify 6 Kaggle CSVs into `matches`/`players` DataFrames | `load_dataset()`, `load_matches()`, `load_players()`, `Dataset` |
| normalization.py | Team-name canonicalization, accent stripping, name matching | `normalize_team_name()`, `strip_accents()`, `clean_display_name()`, `team_matches()` |
| knowledge_graph.py | In-memory query engine over matches + players | `KnowledgeGraph`, `find_matches`, `head_to_head`, `team_record`, `standings`, `search_players`, `average_goals`, `biggest_wins`, `dedupe_matches` |
| server.py | FastMCP MCP server exposing tools over stdio | `mcp`, `get_graph()`, 15 `@mcp.tool()` functions |
| formatting.py | Render engine dicts into spec-shaped answer text | `format_matches`, `format_standings`, `format_players`, `format_head_to_head`, ... |
| demo.py | Standalone CLI demo invoking the tools without an MCP client | `main()` |
| conftest.py | Session-scoped `kg` fixture | `kg` |
| test_data_loader.py | Loader integrity + schema tests | 8 test functions |
| test_normalization.py | Name normalization/matching tests | 8 test functions |
| test_knowledge_graph.py | Query-engine behavior + known-result tests | 23 test functions |
| test_server.py | MCP tool registration + text-output tests | 10 test functions |
