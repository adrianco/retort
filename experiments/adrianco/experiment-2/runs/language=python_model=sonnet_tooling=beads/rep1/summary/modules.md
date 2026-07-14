# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | FastMCP server defining 16 query tools over the soccer datasets | `app`, `find_matches`, `get_team_stats`, `find_players`, `get_league_standings`, `get_competition_summary`, … |
| data_loader.py | Loads/caches the 6 Kaggle CSVs and normalizes team names | `store` (DataStore), `normalize_team_name()`, `team_matches()`, `load_*()` |
| test_server.py | BDD-style pytest suite (51 tests) exercising loaders + tools | `TestDataLoader`, `TestMatchQueries`, `TestTeamStats`, `TestPlayerQueries`, `TestCompetitionQueries`, `TestStatisticalAnalysis`, `TestIntegration` |
