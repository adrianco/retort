# Interfaces

## MCP tools

| Tool | Required args | Optional args | Handler |
|------|---------------|---------------|---------|
| `find_matches` | (none) | team, home_team, away_team, date_from, date_to, competition, season | `matches.go:FindMatchesTool` |
| `get_team_stats` | team | competition, season, venue (home/away/both) | `teams.go:GetTeamStatsTool` |
| `find_players` | (none) | name, nationality, club, position, min_overall, limit | `players.go:FindPlayersTool` |
| `get_head_to_head` | team1, team2 | competition, season | `headtohead.go:GetHeadToHeadTool` |
| `get_standings` | season | competition (default brasileirao) | `standings.go:GetStandingsTool` |
| `get_statistics` | stat_type | competition, season, limit | `stats.go:GetStatisticsTool` |

`stat_type` ∈ {biggest_wins, avg_goals, best_home_record, best_away_record}.

## Data schema (in-memory, loaded from CSV)

`Match`: Date, HomeTeam, AwayTeam, HomeGoal, AwayGoal, Competition, Season, Round.
`Player`: ID, Name, Age, Nationality, Overall, Potential, Club, Position.

## Data sources

Six CSVs under `data/kaggle/` loaded at startup: Brasileirao_Matches, Brazilian_Cup_Matches,
Libertadores_Matches, BR-Football-Dataset, novo_campeonato_brasileiro (matches) and fifa_data (players).
