# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | FastMCP server; registers 13 MCP tools wrapping the query engine | `build_server()`, `get_graph()`, `main()`, `tool_*` functions |
| knowledge_graph.py | In-memory indexed query engine over matches/players (the "graph") | `KnowledgeGraph`, `TableRow`, `resolve_competition()` |
| data_loader.py | Reads the six Kaggle CSVs into normalized `Match`/`Player` records | `load_matches()`, `load_players()`, `Match`, `Player`, `default_data_dir()` |
| formatters.py | Renders query results into the human-readable answer formats from TASK.md | `format_matches()`, `format_head_to_head()`, `format_team_stats()`, `format_standings()`, `format_players()`, `format_average_goals()`, `format_best_record()` |
| team_names.py | Normalizes team names (state suffixes, accents) for cross-dataset matching | `normalize_team()`, `display_team()`, `strip_state_suffix()`, `teams_match()` |
| demo.py | CLI demo exercising several queries against the loaded graph | `main()` |
| conftest.py | Pytest session-scoped fixture loading the shared knowledge graph | `kg` fixture |
| tests/test_data_loader.py | CSV parsing / normalization tests | test functions |
| tests/test_match_queries.py | `find_matches` / `match_between` tests | test functions |
| tests/test_team_queries.py | `team_stats` / `head_to_head` / `compare_teams` tests | test functions |
| tests/test_player_queries.py | `search_players` / `top_players` tests | test functions |
| tests/test_competition_queries.py | `standings` / `champion` / `list_seasons` tests | test functions |
| tests/test_statistics.py | `biggest_wins` / `average_goals` / `best_record` tests | test functions |
| tests/test_server_tools.py | MCP tool-wrapper integration tests | test functions |
| tests/test_team_names.py | Name-normalization unit tests | test functions |
