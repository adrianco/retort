# Interfaces

## MCP tools (JSON-RPC over stdio)

Registered via `[McpServerTool]` and discovered with `WithToolsFromAssembly()`.

| Tool | Purpose | Handler |
|------|---------|---------|
| `search_matches` | Find matches by team/opponent/competition/season/date range | `MatchTools.SearchMatches` |
| `head_to_head` | Head-to-head W/D/L record between two teams | `MatchTools.HeadToHead` |
| `team_record` | A team's W/L/D + goals, filterable by comp/season/home-away | `MatchTools.TeamRecord` |
| `compare_teams` | H2H plus each team's overall record | `MatchTools.CompareTeams` |
| `list_teams` | Distinct team names in scope | `MatchTools.ListTeams` |
| `search_players` | Search FIFA players by (partial) name | `PlayerTools.SearchPlayers` |
| `players_by_nationality` | Players of a nationality, sorted by overall | `PlayerTools.PlayersByNationality` |
| `players_by_club` | Players at a club, sorted by overall | `PlayerTools.PlayersByClub` |
| `top_players` | Top-rated players, filterable by nationality/club/position | `PlayerTools.TopPlayers` |
| `standings` | Calculated league table for a season | `StatsTools.Standings` |
| `biggest_wins` | Largest goal-margin victories | `StatsTools.BiggestWins` |
| `average_goals` | Avg goals/match + home/away/draw rates | `StatsTools.AverageGoals` |
| `best_records` | Teams ranked by win rate (home/away split) | `StatsTools.BestRecords` |

13 tools total.

## Library API (Data core)

- `DataStore.Load(dataDir?)` → loads all matches + players.
- `MatchQueryService`: `Find(MatchFilter)`, `HeadToHead(a,b,filter)`, `TeamRecord(team,filter,side)`, `ListTeams()`.
- `PlayerQueryService`: `SearchByName`, `ByNationality`, `ByClub`, `TopPlayers`.
- `StatsQueryService`: `GetStandings`, `GetBiggestWins`, `GetAverageGoals`, `RankTeamsByRecord`.

## Data sources (read-only CSV)

| File | Loaded as | Competition |
|------|-----------|-------------|
| Brasileirao_Matches.csv | matches | Brasileirao |
| Brazilian_Cup_Matches.csv | matches | CopaDoBrasil |
| Libertadores_Matches.csv | matches | Libertadores |
| BR-Football-Dataset.csv | matches | BRFootballDataset |
| novo_campeonato_brasileiro.csv | matches | HistoricoBrasileirao |
| fifa_data.csv | players | — |

## HTTP routes / CLI commands

(none — MCP stdio server; only CLI arg is `--data-dir=`)
