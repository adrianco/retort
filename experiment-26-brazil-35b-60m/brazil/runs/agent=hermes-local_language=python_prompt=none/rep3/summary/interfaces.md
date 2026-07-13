# Interfaces

## HTTP routes

(none) — this is an MCP (stdio) server, not an HTTP service.

## MCP tools

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| `search_matches` | team, opponent, competition, season, date_from, date_to, limit | JSON list of matches | `query_handlers.find_matches` |
| `get_team_stats` | team, competition, season | JSON W/L/D + goals + win_rate | `query_handlers.get_team_statistics` |
| `get_head_to_head` | team1, team2, competition | JSON H2H record + match list | `query_handlers.get_head_to_head` |
| `search_players` | name, nationality, club, position, min_rating, max_results | JSON list of players | `query_handlers.search_players` |
| `get_standings` | competition, season | JSON standings sorted by points | `query_handlers.get_standings` |
| `get_biggest_wins` | limit | JSON matches by goal diff | `query_handlers.get_biggest_wins` |
| `get_average_goals` | competition | JSON avg goals + home/away/draw rates | `query_handlers.get_average_goals` |
| `get_best_away_record` | limit | JSON away records by win rate | `query_handlers.get_best_away_record` |
| `get_brazilian_players_by_club` | — | JSON Brazilian players per club | `query_handlers.get_brazilian_players_by_club` |
| `list_teams` | — | JSON sorted team names | `query_handlers.get_team_names` |
| `list_competitions` | — | JSON sorted competition names | inline in `server.py` |

## Data schema

Unified match frame (concatenated from 5 CSVs): `date`, `home_team`, `away_team`, `home_goal`, `away_goal`, `competition`, `season`, `round`, `stage`, `source`.
Players frame (from `fifa_data.csv`): `name`, `age`, `nationality`, `overall`, `potential`, `club`, `position`, `jersey_number`, `height`, `weight`.
