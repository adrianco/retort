# Interfaces

The server exposes its capabilities as MCP tools. There are no HTTP routes or CLI subcommands; the process runs as an MCP stdio server (`Program.cs` uses `AddMcpServer().WithStdioServerTransport().WithToolsFromAssembly()`). A single startup arg `--data-dir <path>` (or env var `BRAZILIAN_SOCCER_DATA_DIR`) selects the CSV data directory.

## MCP tools

All tools are declared in `src/BrazilianSoccerMcp.Server/SoccerTools.cs` (methods annotated `[McpServerTool]`) and return plain-text strings formatted by `ResponseFormatter`.

| Tool | Description | Backing service |
|------|-------------|-----------------|
| `FindMatches` | Find matches for a team, optionally filtered by opponent, season, competition. | `MatchQueryService.FindMatches` |
| `GetHeadToHead` | Head-to-head record between two teams: wins/draws/losses + match list. | `MatchQueryService.GetHeadToHead` |
| `GetTeamRecord` | Team win/loss/draw record and goals for/against; season/competition/home-only/away-only filters. | `TeamQueryService.GetRecord` |
| `SearchPlayersByName` | Search players by name (partial, accent-insensitive). | `PlayerQueryService.SearchByName` |
| `FindPlayersByNationality` | List players filtered by nationality. | `PlayerQueryService.FilterByNationality` |
| `FindPlayersByClub` | List players at a given club (partial match). | `PlayerQueryService.FilterByClub` |
| `GetTopRatedPlayers` | Top-rated players by FIFA overall; optional nationality/club/position filters. | `PlayerQueryService.TopRated` |
| `GetStandings` | Final standings table for a competition and season, computed from matches. | `CompetitionQueryService.GetStandings` |
| `GetChampion` | Champion of a competition and season, computed from matches. | `CompetitionQueryService.GetChampion` |
| `GetAverageGoalsPerMatch` | Average goals per match; optional competition/season filters. | `StatisticsQueryService.AverageGoalsPerMatch` |
| `GetBiggestWins` | Biggest wins (largest goal difference); optional competition/season filters. | `StatisticsQueryService.BiggestWins` |
| `GetBestHomeRecord` | Rank teams by home win rate; optional competition/season, min-matches threshold. | `StatisticsQueryService.BestHomeRecord` |
| `GetBestAwayRecord` | Rank teams by away win rate; optional competition/season, min-matches threshold. | `StatisticsQueryService.BestAwayRecord` |

`GetStandings` and `GetChampion` return an inline error string when the competition name cannot be parsed; `GetBestHomeRecord`/`GetBestAwayRecord` share the private `FormatRankedTeamRecords` helper. Free-text `competition` arguments are resolved via `CompetitionParser.Parse` before reaching the service.

## Data schema

Loaded in-memory from CSV; no persistence layer.

`MatchRecord`: HomeTeamRaw, AwayTeamRaw, HomeTeamKey, AwayTeamKey, HomeTeamDisplay, AwayTeamDisplay, HomeGoals (int?), AwayGoals (int?), Date (DateTime?), Season (int?), Competition (enum), Source (enum), Round, Stage, Arena, HomeState, AwayState; computed `Outcome`.

`PlayerRecord`: Id, Name, Age, Nationality, Overall, Potential, Club, Position, JerseyNumber, Height, Weight.

Enums: `Competition` (Unknown, Brasileirao, CopaDoBrasil, Libertadores, SerieB, SerieC), `MatchSource` (five source datasets), `MatchOutcome` (Unknown, HomeWin, AwayWin, Draw).

Query DTOs: `TeamRecord` (with `WinRate`), `HeadToHeadResult`, `StandingsEntry` (with `GoalDifference`).
