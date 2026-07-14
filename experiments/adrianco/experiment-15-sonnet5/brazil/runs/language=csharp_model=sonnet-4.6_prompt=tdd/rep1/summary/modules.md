# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| BrazilianSoccerMCP.Server/Program.cs | MCP stdio host bootstrap; DI wiring; data-path discovery | top-level statements, `FindDataPath()` |
| BrazilianSoccerMCP.Server/Services/CsvDataLoader.cs | Parses the 6 Kaggle CSVs into `UnifiedMatch`/`FifaPlayer` (BOM, multi date formats, quoted ints) | `LoadBrazileiraMatches`, `LoadCupMatches`, `LoadLibertadoresMatches`, `LoadExtendedMatches`, `LoadHistoricalMatches`, `LoadFifaPlayers` |
| BrazilianSoccerMCP.Server/Services/DataRepository.cs | In-memory query engine over matches/players (find, stats, standings, head-to-head) | `LoadAll`, `FindMatchesByTeam`, `FindHeadToHead`, `GetTeamStats`, `GetCompetitionStandings`, `GetHomeAwayStats`, `FindPlayersBy*` |
| BrazilianSoccerMCP.Server/Services/TeamNameNormalizer.cs | Strips state suffixes (`-SP`) and diacritics for fuzzy team matching | `Normalize`, `ContainsTeam` |
| BrazilianSoccerMCP.Server/Tools/MatchQueryTools.cs | MCP tools for match search, head-to-head, date range, biggest wins | `SearchMatchesByTeam`, `FindHeadToHead`, `FindMatchesByDateRange`, `GetBiggestWins` |
| BrazilianSoccerMCP.Server/Tools/TeamQueryTools.cs | MCP tools for team stats, home record, standings, competition stats | `GetTeamStats`, `GetHomeRecord`, `GetCompetitionStandings`, `GetCompetitionStats` |
| BrazilianSoccerMCP.Server/Tools/PlayerQueryTools.cs | MCP tools for player search by name/nationality/club | `FindPlayersByName`, `FindPlayersByNationality`, `FindPlayersByClub`, `GetTopBrazilianPlayersAtBrazilianClubs` |
| BrazilianSoccerMCP.Server/Tools/StatisticsTools.cs | MCP tools for aggregate stats (avg goals, home/away, season matches) | `GetAverageGoals`, `GetHomeAwayStats`, `GetSeasonMatches` |
| BrazilianSoccerMCP.Server/Models/*.cs | POCOs: `UnifiedMatch`, `TeamStats`, `HomeAwayStats`, `FifaPlayer` | model classes |
| BrazilianSoccerMCP.Tests/DataLoadingTests.cs | Loader integration tests against real CSVs | 9 test methods |
| BrazilianSoccerMCP.Tests/MatchQueryTests.cs | Match/team query tests | 7 test methods |
| BrazilianSoccerMCP.Tests/PlayerQueryTests.cs | Player query tests | 6 test methods |
| BrazilianSoccerMCP.Tests/StatisticsTests.cs | Stats/standings tests | 5 test methods |
| BrazilianSoccerMCP.Tests/TeamNameNormalizerTests.cs | Normalizer unit tests (theories) | 4 methods / 16 cases |
| BrazilianSoccerMCP.Tests/TestHelpers.cs | Locates `data/kaggle` from source dir | `FindDataPath` |
| BrazilianSoccerMCP.Tests/UnitTest1.cs | Leftover xUnit template (empty) | `Test1` (no-op) |
