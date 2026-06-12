# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer/__init__.py | Package marker (empty) | — |
| brazilian_soccer/normalize.py | Team-name / date normalization (accent, state-suffix, DD/MM/YYYY) | `strip_accents()`, `normalize_team_name()`, `team_key()`, `key_matches()`, `names_match()`, `state_suffix()`, `parse_date()`, `year_of()` |
| brazilian_soccer/data_loader.py | Per-file CSV loaders into uniform `Match`/`Player`; cross-source de-dup | `Match`, `Player`, `load_all_matches()`, `load_all_players()`, per-file `load_*()` |
| brazilian_soccer/knowledge_base.py | Query + analytics layer over in-memory matches/players | `SoccerKB` (`find_matches`, `head_to_head`, `team_record`, `standings`, `search_players`, `competition_stats`, `biggest_wins`, `list_competitions`, `list_seasons`) |
| brazilian_soccer/service.py | Format `SoccerKB` results into human-readable answers (MCP-agnostic) | `answer_find_matches()`, `answer_head_to_head()`, `answer_team_record()`, `answer_standings()`, `answer_search_players()`, `answer_competition_stats()`, `answer_biggest_wins()`, `answer_list_competitions()`, `answer_list_seasons()` |
| brazilian_soccer/server.py | FastMCP server wiring; registers 9 tools delegating to `service` | `build_server()`, `main()` |
| tests/test_normalize.py | Unit tests for normalization | 14 test functions |
| tests/test_data_loader.py | Unit tests for CSV loaders / dataclasses | ~16 test functions |
| tests/test_knowledge_base.py | Unit tests for query/analytics | ~24 test functions |
| tests/test_service.py | Unit tests for answer formatting | ~12 test functions |
| tests/test_server.py | FastMCP tool-registration / call smoke tests | 5 test functions |
| tests/test_integration.py | End-to-end against real `data/kaggle` CSVs | ~27 test functions |
