# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BrazilianSoccerMcp.Server/Program.cs | Host bootstrap: DI wiring, stdio MCP transport, tool auto-registration | top-level statements |
| src/BrazilianSoccerMcp.Server/Tools/MatchTools.cs | MCP tools for match search + head-to-head | `search_matches`, `head_to_head` |
| src/BrazilianSoccerMcp.Server/Tools/TeamTools.cs | MCP tools for team record + comparison | `team_record`, `compare_teams` |
| src/BrazilianSoccerMcp.Server/Tools/PlayerTools.cs | MCP tools for player search + filtering | `search_players`, `top_rated_players`, `brazilian_players_at_brazilian_clubs` |
| src/BrazilianSoccerMcp.Server/Tools/CompetitionTools.cs | MCP tool for computed standings | `standings` |
| src/BrazilianSoccerMcp.Server/Tools/StatisticsTools.cs | MCP tools for aggregate statistics | `average_goals_per_match`, `best_home_record`, `best_away_record`, `biggest_wins` |
| src/BrazilianSoccerMcp.Core/Data/SoccerDataRepository.cs | Loads all CSVs, dedupes overlapping datasets, holds in-memory match/player collections | `LoadFromDefaultLocation()`, `LoadFromDirectory()` |
| src/BrazilianSoccerMcp.Core/Data/MatchCsvLoader.cs | Per-file CSV match parsers | `LoadBrasileiraoMatches()`, `LoadBrazilianCupMatches()`, `LoadLibertadoresMatches()`, `LoadBrFootballDataset()`, `LoadNovoCampeonatoBrasileiro()` |
| src/BrazilianSoccerMcp.Core/Data/PlayerCsvLoader.cs | FIFA player CSV parser | `LoadFifaPlayers()` |
| src/BrazilianSoccerMcp.Core/Data/TeamNameNormalizer.cs | Accent/case folding + collision-aware team name normalization | `Normalize()`, `IsKnownBrazilianClub()` |
| src/BrazilianSoccerMcp.Core/Data/FlexibleDateParser.cs | Parses ISO, Brazilian day-first, and datetime formats | `Parse()` |
| src/BrazilianSoccerMcp.Core/Data/DataPathResolver.cs | Walks up to locate `data/kaggle` | `Resolve()` |
| src/BrazilianSoccerMcp.Core/Data/RawMatchRow.cs | CsvHelper row DTO | `RawMatchRow` |
| src/BrazilianSoccerMcp.Core/Services/MatchQueryService.cs | Match filtering + head-to-head aggregation | `FindMatches()`, `GetHeadToHead()` |
| src/BrazilianSoccerMcp.Core/Services/TeamQueryService.cs | Team W/L/D + goals-for/against record | `GetTeamRecord()` |
| src/BrazilianSoccerMcp.Core/Services/CompetitionQueryService.cs | Standings computed from matches (3-1-0) | `GetStandings()` |
| src/BrazilianSoccerMcp.Core/Services/PlayerQueryService.cs | Player search + nationality/club/position filtering | `SearchByName()`, `FilterByNationality()`, `FilterByClub()`, `TopRated()` |
| src/BrazilianSoccerMcp.Core/Services/StatisticsService.cs | Aggregate stats: goal averages, best home/away, biggest wins | `GetGoalAverages()`, `BestRecord()`, `BiggestWins()` |
| src/BrazilianSoccerMcp.Core/Services/CompetitionNameParser.cs | Maps competition name strings to enum | `TryParse()` |
| src/BrazilianSoccerMcp.Core/Services/ResponseFormatter.cs | Formats query results into human-readable text | `FormatMatches()`, `FormatHeadToHead()`, `FormatTeamRecord()`, `FormatStandings()`, `FormatPlayers()` |
| src/BrazilianSoccerMcp.Core/Models/*.cs | Domain records: `MatchRecord`, `PlayerRecord`, `NormalizedTeam`, `Competition` | (record/enum types) |
| tests/BrazilianSoccerMcp.Tests/*.cs | 10 BDD-style xUnit test classes over services + parsers | 41 `[Fact]`/`[Theory]` methods |
