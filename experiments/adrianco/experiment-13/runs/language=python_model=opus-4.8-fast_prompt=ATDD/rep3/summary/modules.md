# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | MCP server; thin FastMCP adapter exposing 8 tools over stdio | `mcp`, `main()`, `find_matches`, `get_team_record`, `compare_teams`, `search_players`, `get_standings`, `get_competition_summary`, `list_team_competitions`, `get_team_profile` |
| soccer_service.py | Domain service turning normalized tables into answer dicts | `SoccerService` (`find_matches`, `get_team_record`, `compare_teams`, `list_team_competitions`, `search_players`, `get_standings`, `get_competition_summary`, `get_team_profile`) |
| soccer_data.py | Data access; loads 6 Kaggle CSVs into two normalized pandas tables, de-duplicates overlapping sources | `SoccerRepository`, `SoccerRepository.default()`, `SoccerRepository.from_dir()` |
| team_names.py | Team-name normalization (accents, suffixes, aliases) | `normalize_team()`, `strip_accents()` |
| demo.py | CLI demo printing sample answers via `SoccerService` | `main()` |
| tests/conftest.py | Pytest fixtures; connects an MCP client over the real protocol | `client` fixture, `SyncMCPClient` |
| tests/test_acceptance.py | Executable acceptance tests through the MCP tools | 24 test functions |
| tests/test_unit.py | Unit tests for normalization + repository internals | 7 test functions |
