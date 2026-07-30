# Interfaces

## MCP transport

JSON-RPC 2.0 over stdio. Methods: `initialize`, `ping`, `tools/list`, `tools/call`,
and the notifications `notifications/initialized`, `notifications/cancelled`, `$/progress`
(silently accepted). `initialize` echoes the client's `protocolVersion` and advertises a
`tools` capability.

## MCP tools (`tools/call`)

| Tool | Purpose | Key arguments |
|------|---------|---------------|
| search_matches | Match search across all 5 CSVs | team, opponent, home_team, away_team, competition, season, date_from, date_to, round, stage, limit |
| team_statistics | W/L/D, points, goals for/against | team (req), season, competition, venue (all/home/away) |
| head_to_head | Two-team record + recent meetings | team_a (req), team_b (req), competition, season, limit |
| search_players | FIFA player search, sorted by overall | name, nationality, club, position, limit |
| get_standings | Season table computed from matches | competition (req), season (req) |
| team_rankings | Rank teams by a metric | competition, season, metric (points/goals_for/home_win_rate/away_win_rate), limit |
| competition_statistics | Goal averages, home/draw/away rates | competition, season |
| biggest_wins | Largest winning margins | competition, season, limit |
| find_derbies | Traditional Brazilian derby fixtures | season, competition, limit |
| team_competitions | Competitions a team appears in | team (req) |
| data_summary | Loaded match/player counts by source | (none) |

## Data schema (in-memory)

- `Match`: date, competition, season, round, stage, home_team, away_team, home_goals,
  away_goals, source, venue, optional home/away corners & shots.
- `Player`: id, name, age, nationality, overall, potential, club, position, jersey_number,
  height, weight.

## Data sources loaded

`Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`,
`BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv`, `fifa_data.csv` — all under
`data/kaggle/`.
