# Interfaces

## MCP tools (registered in `server.py` via `@mcp.tool()`)

| Tool | Purpose | Key args |
|------|---------|----------|
| `search_matches` | Find matches by team/opponent/competition/season/date range | team, opponent, competition, season, start_date, end_date, role, limit |
| `get_team_stats` | W/L/D record + goals for/against for a team | team, competition, season, role |
| `head_to_head` | Head-to-head record + recent matches between two teams | team1, team2, competition, season, limit |
| `get_competition_standings` | League table computed from match results | season, competition |
| `search_players` | FIFA player search | name, nationality, club, position, min_overall, limit |
| `top_scoring_teams` | Teams ranked by total goals | competition, season, top_n |
| `biggest_wins` | Matches with largest goal margins | competition, season, top_n |
| `aggregate_stats` | Goals/match, home/draw/away win rates | competition, season |
| `best_home_records` | Teams ranked by home win rate (min 5 home games) | competition, season, top_n |

All tools return JSON strings (`json.dumps`, `ensure_ascii=False`).

## Library API

- `data_loader.SoccerData` — lazy-loading container; properties `brasileirao`, `cup`, `libertadores`, `br_football`, `historico`, `fifa`, `all_matches`.
- `data_loader.normalize_team(name)` — canonical lowercase team key; alias table + state-suffix/parenthetical stripping.
- `data_loader.get_data()` — module-level singleton accessor used by every tool.

## Data schema (normalized match frame)

Columns added by the loader: `datetime`, `date`, `home_team`, `away_team`, `home_norm`, `away_norm`, `home_goal`, `away_goal`, `competition`, `season`, `round`, `source`.
