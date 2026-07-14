# Interfaces

## MCP tools

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| `find_matches` | team, opponent, competition, season, date_from, date_to, limit | text listing of matches (+ H2H summary when two teams given) | `server.py:find_matches` |
| `get_team_stats` | team, competition, season | text W/D/L record, goals for/against, home/away split | `server.py:get_team_stats` |
| `find_players` | name, nationality, club, position, min_rating, limit | text listing of FIFA players with ratings | `server.py:find_players` |
| `get_standings` | competition, season | text points table computed from match results | `server.py:get_standings` |
| `get_head_to_head` | team1, team2, competition, season, limit | text H2H record + recent matches | `server.py:get_head_to_head` |
| `get_top_stats` | stat_type, competition, season, limit | text aggregate stats (biggest_wins, averages, best_home, best_away, top_scoring, most_matches) | `server.py:get_top_stats` |

Transport: stdio via `mcp.run()` (`server.py:434`).

## Data schema

`DataStore` loads six CSVs from `data/kaggle/` and builds `all_matches`, a unified frame with columns:
`date, home_team, away_team, norm_home, norm_away, home_goal, away_goal, competition, season, source`.

Sources unified into `all_matches`: `Brasileirao_Matches`, `Brazilian_Cup_Matches`,
`Libertadores_Matches`, and `novo_campeonato_brasileiro` (only seasons before the Brasileirão file's
earliest season, to avoid double-counting). `BR-Football-Dataset` and `fifa_data` are loaded
into separate frames (`br_football`, `players`); only `players` is queried (by `find_players`).
