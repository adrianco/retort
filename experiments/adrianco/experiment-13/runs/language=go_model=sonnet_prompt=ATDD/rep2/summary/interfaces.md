# Interfaces

## MCP tools (JSON-RPC over stdio)

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| find_matches | team, team1, team2, competition, season, date_from, date_to | `{matches[], total, head_to_head?}` | `mcp/server.go:findMatches` |
| get_team_stats | team (required), competition, season | `{team, matches, wins, draws, losses, goals_for, goals_against, points}` | `mcp/server.go:getTeamStats` |
| find_players | name, nationality, club, limit | `{players[], total}` (sorted by overall desc) | `mcp/server.go:findPlayers` |
| get_standings | competition, season | `{standings[], total}` (computed league table) | `mcp/server.go:getStandings` |
| get_statistics | competition, season | `{total_matches, total_goals, home_wins, away_wins, draws, avg_goals_per_match, home_win_rate}` | `mcp/server.go:getStatistics` |

Protocol methods handled in `ServeStdio`: `initialize`, `tools/list`, `tools/call`, `notifications/initialized`.

## Data schema (in-memory)

- `Match`: Competition, HomeTeam, AwayTeam, HomeGoal, AwayGoal, Season, Date, Round, Stage
- `Player`: ID, Name, Age, Nationality, Overall, Potential, Club, Position, JerseyNumber

## Data sources

Loads 6 CSVs from `data/kaggle/`: Brasileirao_Matches, Brazilian_Cup_Matches, Libertadores_Matches, novo_campeonato_brasileiro, BR-Football-Dataset (all → `Matches`), fifa_data (→ `Players`).
