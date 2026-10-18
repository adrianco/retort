# Interfaces

## Transport

MCP server over stdio (newline-delimited JSON-RPC 2.0). Entry: `java -jar target/brazilian-soccer-mcp-1.0.0.jar [data-directory]` (default data dir `data/kaggle`). Methods handled: `initialize`, `tools/list`, `tools/call`. Unknown methods throw (see flow.md — this path crashes the server).

## MCP tools (registered in `tools()`)

| Tool | Arguments | Returns | Handler |
|------|-----------|---------|---------|
| search_matches | team, opponent, competition, season, from, to, limit | `[Match]` | `SoccerService.matches` |
| team_statistics | team (required), competition, season, home_only | record object | `SoccerService.teamStatistics` |
| head_to_head | team (required), opponent (required), competition, season | h2h object | `SoccerService.headToHead` |
| search_players | name, nationality, club, position, limit | `[player map]` | `SoccerRepository.findPlayers` |
| standings | competition, season | `[row]` | `SoccerService.standings` |
| competition_statistics | competition, season | stats object | `SoccerService.competitionStatistics` |

Each `tools/call` reply wraps data in both `content[0].text` (JSON string) and `structuredContent.data`. No `outputSchema` is declared.

## Data schema

- `Match` record: competition, date, home, away, homeGoals, awayGoals, season, round, stage.
- Players: raw CSV rows kept as `Map<String,String>` (columns: Name, Nationality, Club, Position, Overall, …).

Data sources loaded at startup: `Brasileirao_Matches.csv`, `Brazilian_Cup_Matches.csv`, `Libertadores_Matches.csv`, `BR-Football-Dataset.csv`, `novo_campeonato_brasileiro.csv` (matches) and `fifa_data.csv` (players).
