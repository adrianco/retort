# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer/__init__.py | Package marker | — |
| brazilian_soccer/normalize.py | Canonical team-name normalization (accents, suffixes, alias table) | `normalize_team()`, `teams_match()`, `strip_accents()` |
| brazilian_soccer/data_loader.py | Load 6 Kaggle CSVs into uniform `Match`/`Player` records; tolerant int/date parsing; de-dup overlapping Brasileirão seasons | `Match`, `Player`, `load_all_matches()`, `load_players()`, `parse_date()`, `parse_int()` |
| brazilian_soccer/queries.py | In-memory query engine over matches/players (the "brain") | `KnowledgeBase` (`find_matches`, `head_to_head`, `team_record`, `standings`, `search_players`, `average_goals_per_match`, `biggest_wins`, `best_record`, `summary`) |
| brazilian_soccer/tools.py | Format query results into human-readable answer strings (one method per MCP tool) | `SoccerTools` (10 formatting methods) |
| brazilian_soccer/server.py | FastMCP server registering 10 tools, each delegating to `SoccerTools` | `build_server()`, `main()` |
| tests/test_normalize.py | Unit tests for name normalization | 8 test functions |
| tests/test_data_loader.py | Unit tests for CSV parsing / loaders | 10 test functions |
| tests/test_queries.py | Unit tests for KnowledgeBase query logic | 18 test functions |
| tests/test_tools.py | Unit tests for answer formatting | 8 test functions |
| tests/test_server.py | MCP server wiring / tool registration tests | 4 test functions |
| tests/test_integration_samples.py | End-to-end checks against the real datasets + perf criteria | 12 test functions |

Layered architecture: `server.py` → `tools.py` (formatting) → `queries.py` (logic) → `data_loader.py` + `normalize.py` (data). 6 source modules, 6 test files (60 test functions).
