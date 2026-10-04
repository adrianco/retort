# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | MCP server over stdio (JSON-RPC 2.0); defines 20 query tools and the lifecycle handlers | `main()`, `handle()`, `call_tool()`, `TOOLS`, tool fns (`search_matches`, `head_to_head`, `standings`, `search_players`, `team_profile`, …) |
| soccer_data.py | CSV knowledge base: loads the 6 Kaggle datasets, normalizes team names, answers match/team/player/standings/stats queries | `SoccerDB`, `get_db()`, `Match`, `normalize_team()`, `display_team()`, `parse_date()`, `format_player()`, `load_matches()`, `load_players()` |
| test_soccer.py | pytest suite: normalization, data coverage, 25 sample-question scenarios, performance, MCP stdio E2E | 33 test functions (58 cases after parametrization) |
| README.md | Usage / run instructions | n/a |
| data/kaggle/*.csv | Provided datasets (5 match files + fifa_data.csv) | n/a |
