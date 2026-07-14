# Interfaces

## MCP tools (stdio transport)

Registered via `WithToolsFromAssembly` over classes marked `[McpServerToolType]`; each method is an `[McpServerTool]`. All return human-readable `string`.

| Tool | Args | Handler |
|------|------|---------|
| SearchMatchesByTeam | teamName, competition?, season?, maxResults=20 | `MatchQueryTools` |
| FindHeadToHead | team1, team2, maxResults=20 | `MatchQueryTools` |
| FindMatchesByDateRange | fromDate, toDate, maxResults=50 | `MatchQueryTools` |
| GetBiggestWins | competition?, count=10 | `MatchQueryTools` |
| GetTeamStats | teamName, competition?, season? | `TeamQueryTools` |
| GetHomeRecord | teamName, competition?, season? | `TeamQueryTools` |
| GetCompetitionStandings | competition, season | `TeamQueryTools` |
| GetCompetitionStats | competition?, season? | `TeamQueryTools` |
| FindPlayersByName | name, maxResults=10 | `PlayerQueryTools` |
| FindPlayersByNationality | nationality, maxResults=20 | `PlayerQueryTools` |
| FindPlayersByClub | club, maxResults=20 | `PlayerQueryTools` |
| GetTopBrazilianPlayersAtBrazilianClubs | perClub=5 | `PlayerQueryTools` |
| GetAverageGoals | competition?, season? | `StatisticsTools` |
| GetHomeAwayStats | competition?, season? | `StatisticsTools` |
| GetSeasonMatches | season, competition?, maxResults=50 | `StatisticsTools` |

15 tools total (the stdout summary's "8 tools" undercounts).

## Data schema (in-memory)

- `UnifiedMatch`: DateTime, HomeTeam, AwayTeam, HomeGoal, AwayGoal, Season, Competition, Round?, Stage?; derived Result/GoalDifference/TotalGoals.
- `FifaPlayer`: Id, Name, Age, Nationality, Overall, Potential, Club, Position, Value, ... (15 fields).
- `TeamStats`: Played/Wins/Draws/Losses/GoalsFor/GoalsAgainst; derived Points, GoalDifference, WinRate.
- `HomeAwayStats`: totals + derived rates + AverageGoalsPerMatch.

## Data sources

`data/kaggle/`: Brasileirao_Matches.csv, Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv (extended), novo_campeonato_brasileiro.csv (historical), fifa_data.csv.
