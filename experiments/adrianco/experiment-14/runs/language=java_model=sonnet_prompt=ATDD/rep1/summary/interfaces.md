# Interfaces

## MCP tools (stdio transport)

| Tool | Args | Returns | Handler |
|------|------|---------|---------|
| findMatches | team, homeTeam, awayTeam, competition, season, dateFrom, dateTo, limit | formatted match list | `BrazilianSoccerMcpServer:findMatches` → `MatchService.findMatches` |
| getTeamStats | team (required), competition, season | W/L/D, goals, points | `MatchService.getTeamStats` |
| findPlayers | name, nationality, club, position, minOverall, limit | formatted player list | `PlayerService.findPlayers` |
| getStandings | season, competition, limit | standings table | `MatchService.getStandings` |
| getHeadToHead | team1 (required), team2 (required), competition, season | h2h W/L/D + goals + recent | `MatchService.getHeadToHead` |
| getStatistics | statType (required: biggest_wins\|avg_goals\|home_record), competition, season | aggregate stats text | `MatchService.getStatistics` |

Server registered via `McpServer.sync(StdioServerTransportProvider)` with serverInfo "Brazilian Soccer MCP 1.0.0".

## Data schema (in-memory models)

- `Match`: competition, date, homeTeam, awayTeam, homeGoals, awayGoals, season, round, stage, arena.
- `Player`: name, age, nationality, overall, potential, club, position.
- `TeamStats`: team, matchesPlayed, wins, draws, losses, goalsScored, goalsConceded; derived points/goalDifference.
- `Standing`: position + TeamStats.

## Data sources loaded

Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv (2003–2011 only, dedup), Brazilian_Cup_Matches.csv, Libertadores_Matches.csv, BR-Football-Dataset.csv, fifa_data.csv (BOM-stripped).
