# Modules

C#/.NET solution `BrazilianSoccerMcp.slnx` with three projects: a testable `Data` core library, an MCP `Server` host, and an xUnit `Tests` project.

## `BrazilianSoccerMcp.Data` (core library)

| Path | Purpose | Entry points |
|------|---------|--------------|
| Csv/CsvTable.cs | Hand-rolled CSV parser (quoted fields, BOM, UTF-8) | `CsvTable`, `CsvTable.Load()` |
| DataPathResolver.cs | Locates `data/kaggle` dir via override/env/upward walk | `DataPathResolver.Resolve()` |
| DataStore.cs | Holds all loaded matches + players for process lifetime | `DataStore`, `DataStore.Load()` |
| Loading/FlexibleDateParser.cs | Parses ISO / Brazilian / with-time date formats | `FlexibleDateParser` |
| Loading/MatchDataLoader.cs | Loads all 5 match CSVs into `MatchRecord`s | `MatchDataLoader.LoadAll()` |
| Loading/PlayerDataLoader.cs | Loads `fifa_data.csv` into `PlayerRecord`s | `PlayerDataLoader.Load()` |
| Models/Competition.cs | Competition enum + display names | `Competition`, `CompetitionExtensions` |
| Models/MatchRecord.cs | Match row model (teams, goals, date, season) | `MatchRecord` |
| Models/MatchResult.cs | Home-win / away-win / draw result enum | `MatchResult` |
| Models/PlayerRecord.cs | FIFA player row model | `PlayerRecord` |
| Normalization/TeamNameNormalizer.cs | Unifies team-name variants (accents, state suffixes, full names) | `TeamNameNormalizer` |
| Queries/MatchFilter.cs | Filter record (team, opponent, competition, season, dates) | `MatchFilter` |
| Queries/MatchQueryService.cs | Match search, head-to-head, team-record | `Find`, `HeadToHead`, `TeamRecord`, `ListTeams` |
| Queries/PlayerQueryService.cs | Player search/filter over FIFA data | `SearchByName`, `ByNationality`, `ByClub`, `TopPlayers` |
| Queries/StatsQueryService.cs | Standings, biggest wins, goal averages, rankings | `GetStandings`, `GetBiggestWins`, `GetAverageGoals`, `RankTeamsByRecord` |
| Queries/HeadToHeadResult.cs / StandingRow.cs | Query result records | `HeadToHeadResult`, `StandingRow`, `TeamRecordResult` |
| Formatting/ResponseFormatter.cs | Formats query results as human-readable strings | `ResponseFormatter` |

## `BrazilianSoccerMcp.Server` (MCP host)

| Path | Purpose | Entry points |
|------|---------|--------------|
| Program.cs | Host builder, DI wiring, MCP stdio transport | top-level program |
| Tools/MatchTools.cs | MCP tools for match/team queries | `search_matches`, `head_to_head`, `team_record`, `compare_teams`, `list_teams` |
| Tools/PlayerTools.cs | MCP tools for player queries | `search_players`, `players_by_nationality`, `players_by_club`, `top_players` |
| Tools/StatsTools.cs | MCP tools for aggregate stats | `standings`, `biggest_wins`, `average_goals`, `best_records` |

## `BrazilianSoccerMcp.Tests` (xUnit)

| Path | Purpose | Entry points |
|------|---------|--------------|
| Csv/CsvTableTests.cs | CSV parser unit tests | 5 tests |
| Loading/DataLoadingTests.cs | Dataset load / integrity tests | 6 tests |
| Normalization/TeamNameNormalizerTests.cs | Name-normalization tests | 7 tests (+ InlineData) |
| Queries/MatchQueryServiceTests.cs | Match/H2H/record tests | 9 tests |
| Queries/PlayerQueryServiceTests.cs | Player query tests | 6 tests |
| Queries/StatsQueryServiceTests.cs | Standings/stats tests | 6 tests |
| Samples/SampleQuestionsTests.cs | Spec sample-question mapping | 25 tests |
| Performance/PerformanceTests.cs | Response-time checks | 3 tests |
| Fixtures/DataStoreFixture.cs | Shared loaded-data fixture | `DataStoreFixture` |
