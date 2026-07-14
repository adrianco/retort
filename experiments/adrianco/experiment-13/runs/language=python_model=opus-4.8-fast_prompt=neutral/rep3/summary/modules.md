# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| server.py | MCP stdio server; thin tool wrappers over the query engine | `mcp` (FastMCP), 16 `@mcp.tool()` fns, `_selftest()` |
| soccer_data.py | Data layer: load + normalize 6 Kaggle CSVs into `Match`/`Player` records | `SoccerDatabase.load()`, `Match`, `Player`, `canonical_key()`, `normalize_team_name()`, `team_matches()`, `parse_date()`, `split_team()`, `strip_accents()`, `get_db()` |
| soccer_queries.py | Query engine implementing every required capability | `SoccerQueryEngine` (find_matches, last_match, head_to_head, team_record, compare_teams, search_players, players_by_club, players_by_nationality, top_players, standings, list_competitions, list_seasons, competition_stats, biggest_wins, best_record, database_summary) |
| test_soccer.py | pytest suite mirroring the spec's capability groups | 39 test functions (several parametrized; 22 sample-question cases) |

Excluded: `.venv/`, `.ruff_cache/`, `__pycache__/`, `data/` (provided CSVs), `.coverage`.
