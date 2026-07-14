# Modules

## src/BrazilianSoccerMcp.Core

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BrazilianSoccerMcp.Core/Data/SoccerDataStore.cs | In-memory repository over loaded matches/players with team-name-aware lookups | `SoccerDataStore`, `LoadFromDirectory()`, `ResolveTeamKey()`, `GetMatchesForTeam()`, `GetMatchesForTeams()`, `GetDisplayName()` |
| src/BrazilianSoccerMcp.Core/Data/MatchRecord.cs | Normalized match row with computed `Outcome` | `MatchRecord`, `Outcome` |
| src/BrazilianSoccerMcp.Core/Data/PlayerRecord.cs | FIFA player row | `PlayerRecord` |
| src/BrazilianSoccerMcp.Core/Data/Enums.cs | Domain enums | `Competition`, `MatchSource`, `MatchOutcome` |
| src/BrazilianSoccerMcp.Core/Data/MatchDeduplicator.cs | Removes duplicate matches across overlapping datasets | `MatchDeduplicator.Deduplicate()` |
| src/BrazilianSoccerMcp.Core/Data/MatchSourcePriority.cs | Preferred source ordering per competition | `MatchSourcePriority.OrderFor()` |
| src/BrazilianSoccerMcp.Core/Data/CsvLoaderHelpers.cs | Shared CSV parsing helpers | CSV field/record helpers |
| src/BrazilianSoccerMcp.Core/Data/BrasileiraoMatchLoader.cs | Loads `Brasileirao_Matches.csv` | `BrasileiraoMatchLoader.LoadFile()` |
| src/BrazilianSoccerMcp.Core/Data/BrazilianCupMatchLoader.cs | Loads `Brazilian_Cup_Matches.csv` | `BrazilianCupMatchLoader.LoadFile()` |
| src/BrazilianSoccerMcp.Core/Data/LibertadoresMatchLoader.cs | Loads `Libertadores_Matches.csv` | `LibertadoresMatchLoader.LoadFile()` |
| src/BrazilianSoccerMcp.Core/Data/BrFootballDatasetLoader.cs | Loads `BR-Football-Dataset.csv` | `BrFootballDatasetLoader.LoadFile()` |
| src/BrazilianSoccerMcp.Core/Data/NovoCampeonatoBrasileiroLoader.cs | Loads `novo_campeonato_brasileiro.csv` | `NovoCampeonatoBrasileiroLoader.LoadFile()` |
| src/BrazilianSoccerMcp.Core/Data/FifaPlayerLoader.cs | Loads `fifa_data.csv` into `PlayerRecord`s | `FifaPlayerLoader.LoadFile()` |
| src/BrazilianSoccerMcp.Core/Normalization/TeamNameNormalizer.cs | Strips state suffixes/accents to canonical team key + display name | `NormalizeKey()`, `DisplayName()` |
| src/BrazilianSoccerMcp.Core/Normalization/CompetitionParser.cs | Parses free-text competition name to `Competition` enum | `CompetitionParser.Parse()` |
| src/BrazilianSoccerMcp.Core/Normalization/FlexibleDateParser.cs | Parses ISO/Brazilian/with-time date formats | `FlexibleDateParser.Parse()` |
| src/BrazilianSoccerMcp.Core/Normalization/TextNormalizer.cs | Diacritic removal + case folding for matching | `RemoveDiacritics()`, `Fold()` |
| src/BrazilianSoccerMcp.Core/Queries/MatchQueryService.cs | Find matches; compute head-to-head | `FindMatches()`, `GetHeadToHead()` |
| src/BrazilianSoccerMcp.Core/Queries/TeamQueryService.cs | Team W/D/L and goals record | `GetRecord()` |
| src/BrazilianSoccerMcp.Core/Queries/PlayerQueryService.cs | Player search/filter/top-rated | `SearchByName()`, `FilterByNationality()`, `FilterByClub()`, `TopRated()` |
| src/BrazilianSoccerMcp.Core/Queries/CompetitionQueryService.cs | Standings and champion computed from matches | `GetStandings()`, `GetChampion()` |
| src/BrazilianSoccerMcp.Core/Queries/StatisticsQueryService.cs | Aggregate stats (avg goals, biggest wins, home/away records) | `AverageGoalsPerMatch()`, `BiggestWins()`, `HomeWinRate()`, `BestHomeRecord()`, `BestAwayRecord()` |
| src/BrazilianSoccerMcp.Core/Queries/ResponseFormatter.cs | Renders query results as plain-text answers | `FormatMatches()`, `FormatHeadToHead()`, `FormatTeamRecord()`, `FormatPlayers()`, `FormatStandings()` |
| src/BrazilianSoccerMcp.Core/Queries/TeamRecord.cs | Team record DTO with `WinRate` | `TeamRecord` |
| src/BrazilianSoccerMcp.Core/Queries/HeadToHeadResult.cs | Head-to-head DTO | `HeadToHeadResult` |
| src/BrazilianSoccerMcp.Core/Queries/StandingsEntry.cs | Standings-row DTO | `StandingsEntry` |

## src/BrazilianSoccerMcp.Server

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BrazilianSoccerMcp.Server/Program.cs | Host entrypoint; loads data, registers DI services + MCP stdio server | top-level statements |
| src/BrazilianSoccerMcp.Server/SoccerTools.cs | MCP tool surface wrapping the query services | `SoccerTools` (15 `[McpServerTool]` methods) |
| src/BrazilianSoccerMcp.Server/DataDirectoryLocator.cs | Locates the `data/kaggle` CSV directory | `DataDirectoryLocator.Locate()` |

## tests/BrazilianSoccerMcp.Core.Tests

| Path | Purpose | Entry points |
|------|---------|--------------|
| tests/BrazilianSoccerMcp.Core.Tests/TeamNameNormalizerTests.cs | Team name normalization tests | 11 tests |
| tests/BrazilianSoccerMcp.Core.Tests/SoccerDataStoreTests.cs | Data store lookup tests | 7 tests |
| tests/BrazilianSoccerMcp.Core.Tests/MatchQueryServiceTests.cs | Match query/head-to-head tests | 7 tests |
| tests/BrazilianSoccerMcp.Core.Tests/MatchCsvLoadersTests.cs | CSV loader tests | 6 tests |
| tests/BrazilianSoccerMcp.Core.Tests/ResponseFormatterTests.cs | Output formatting tests | 6 tests |
| tests/BrazilianSoccerMcp.Core.Tests/PlayerQueryServiceTests.cs | Player query tests | 5 tests |
| tests/BrazilianSoccerMcp.Core.Tests/CompetitionQueryServiceTests.cs | Standings/champion tests | 4 tests |
| tests/BrazilianSoccerMcp.Core.Tests/MatchDeduplicatorTests.cs | Deduplication tests | 4 tests |
| tests/BrazilianSoccerMcp.Core.Tests/StatisticsQueryServiceTests.cs | Statistics tests | 4 tests |
| tests/BrazilianSoccerMcp.Core.Tests/MatchRecordTests.cs | Match record/outcome tests | 4 tests |
| tests/BrazilianSoccerMcp.Core.Tests/CompetitionParserTests.cs | Competition parsing tests | 3 tests |
| tests/BrazilianSoccerMcp.Core.Tests/FlexibleDateParserTests.cs | Date parsing tests | 3 tests |
| tests/BrazilianSoccerMcp.Core.Tests/TeamQueryServiceTests.cs | Team record tests | 3 tests |
| tests/BrazilianSoccerMcp.Core.Tests/FifaPlayerLoaderTests.cs | FIFA player loader tests | 2 tests |
| tests/BrazilianSoccerMcp.Core.Tests/UnitTest1.cs | Template placeholder | 1 test |
| tests/BrazilianSoccerMcp.Core.Tests/TestData.cs | Shared test fixtures | test helpers |
