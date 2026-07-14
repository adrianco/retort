# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| bsoccer/__init__.py | Package marker | — |
| bsoccer/server.py | MCP server (FastMCP, stdio); exposes the query engine as 11 MCP tools | `mcp`, `find_matches`, `team_record`, `head_to_head`, `search_players`, `players_by_club`, `standings`, `champion`, `list_seasons`, `competition_stats`, `biggest_wins`, `top_scoring_teams`, `main()` |
| bsoccer/queries.py | Query engine over normalized DataFrames (matches, teams, players, competitions, stats) | `QueryEngine` |
| bsoccer/data.py | Loads the 6 Kaggle CSVs into unified/deduped pandas DataFrames | `SoccerData`, `get_data()` |
| bsoccer/normalize.py | Canonical team-name normalization (accent-fold, suffix-strip, alias map) | `normalize_team()`, `display_name()`, `strip_accents()` |
| bsoccer/format.py | Renders structured query results into prose answers | `format_matches`, `format_record`, `format_head_to_head`, `format_players`, `format_standings`, `format_champion`, `format_competition_stats`, `format_biggest_wins`, `format_club_summary` |
| bsoccer/cli.py | Thin argparse CLI mirroring the MCP tools for manual exploration | `build_parser()`, `run()`, `main()` |
| conftest.py | Makes repo root importable for tests | — |
| tests/test_data.py | Data-loading tests | 9 test functions |
| tests/test_normalize.py | Name-normalization tests | 10 test functions |
| tests/test_queries.py | Query-engine tests | 20 test functions |
| tests/test_server.py | MCP tool + formatter tests | 8 test functions |
