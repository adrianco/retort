# Interfaces

## MCP tools (JSON-RPC `tools/call`)

| Tool | Inputs | Returns | Handler |
|------|--------|---------|---------|
| search_matches | team, home_team, away_team, competition, season, date_from, date_to, limit | formatted match list | `query_engine.ex:search_matches` |
| get_team_stats | team (req), competition, season | W/L/D + goals + home/away split | `query_engine.ex:get_team_stats` |
| head_to_head | team1 (req), team2 (req), competition, season | h2h record + recent matches | `query_engine.ex:head_to_head` |
| search_players | name, nationality, club, position, limit | ranked player list | `query_engine.ex:search_players` |
| get_standings | season (req), competition | computed league table | `query_engine.ex:get_standings` |
| get_biggest_wins | competition, season, limit | matches by goal diff | `query_engine.ex:get_biggest_wins` |
| get_summary_stats | competition, season | avg goals, home/away win rates | `query_engine.ex:get_summary_stats` |

## JSON-RPC methods

`initialize`, `notifications/initialized`, `tools/list`, `tools/call`, `ping` — over stdio, newline-delimited (`mcp_server.ex`).

## Data schema (in-memory maps)

- **match**: competition (atom), datetime (ISO string), home_team, away_team, home_goal, away_goal, season, round/stage, optional state/tournament/corner/shot fields.
- **player**: id, name, age, nationality, overall, potential, club, position, jersey_number, + skill/reputation fields.

Sources: 6 CSVs in `data/kaggle/` (Brasileirão, Copa do Brasil, Libertadores, BR-Football extended, historical 2003-2019, FIFA players).
