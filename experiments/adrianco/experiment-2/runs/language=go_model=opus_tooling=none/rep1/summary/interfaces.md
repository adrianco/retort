# Interfaces

## MCP tools (JSON-RPC `tools/call`)

| Tool | Arguments | Returns | Handler |
|------|-----------|---------|---------|
| matches_between | team_a, team_b | matches + H2H summary text | `main.go:callTool` → `MatchesBetween`/`H2H` |
| matches_by_team | team, season?, competition? | filtered match list | `MatchesByTeam` |
| team_stats | team, season?, competition?, home_only?, away_only? | W/D/L, goals, points, win rate | `TeamStats` |
| head_to_head | team_a, team_b | H2H W/W/draws | `H2H` |
| standings | season, competition? | computed league table | `Standings` |
| biggest_wins | limit? | matches by goal difference | `BiggestWins` |
| average_goals | season?, competition? | avg total goals/match | `AverageGoalsPerMatch` |
| find_player | name | players matching name substring | `PlayersByName` |
| top_players | limit?, nationality?, club?, position? | players sorted by Overall | `TopPlayers` |
| players_by_club | club | players whose club matches substring | `PlayersByClub` |

## JSON-RPC methods

`initialize`, `tools/list`, `tools/call`, `ping`. Notifications (no `id`) are ignored.

## Data schema

`Match`: Date, HomeTeam, AwayTeam, HomeGoal, AwayGoal, Season, Round, Competition, Stage, Arena.
`Player`: ID, Name, Age, Nationality, Overall, Potential, Club, Position, JerseyNumber, Height, Weight.

## Datasets ingested (from `$SOCCER_DATA_DIR`, default `data/kaggle`)

Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv, novo_campeonato_brasileiro.csv, fifa_data.csv.
