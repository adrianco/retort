# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| brazilian_soccer/__init__.py | Package docstring + `__all__` | `normalize`, `data_loader`, `queries` |
| brazilian_soccer/__main__.py | `python -m brazilian_soccer` launcher | delegates to `server.main` |
| brazilian_soccer/normalize.py | Team-name / date / goal normalization helpers | `strip_accents`, `normalize_team_name`, `team_key`, `parse_date`, `parse_goal` |
| brazilian_soccer/data_loader.py | Load the 6 Kaggle CSVs into `Match`/`Player` records | `Match`, `Player`, `load_matches()`, `load_players()` |
| brazilian_soccer/queries.py | In-memory query engine (dedup, search, standings, stats) | `KnowledgeGraph`, `canonical_competition`, `display_competition` |
| brazilian_soccer/server.py | MCP tool layer + text formatting | `SoccerService`, `build_server()`, `main()` |
| brazilian_soccer/demo.py | Battery of sample-question answers | `SAMPLE_QUESTIONS`, `main()` |
| tests/conftest.py | Shared fixtures (`fixture_dir`, `real_data_dir`) | 2 fixtures |
| tests/test_normalize.py | Normalization unit tests | 18 test functions |
| tests/test_data_loader.py | CSV-loading unit tests | 11 test functions |
| tests/test_queries.py | KnowledgeGraph query/dedup tests | 24 test functions |
| tests/test_server.py | Tool-logic + MCP-wiring tests | 12 test functions |
| tests/test_demo.py | Demo battery tests | 3 test functions |
