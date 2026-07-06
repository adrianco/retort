# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Executable entry: loads data, creates server, connects over stdio | `main()` |
| src/server.ts | Constructs the McpServer and registers the 8 MCP tools | `createServer()` |
| src/tools.ts | Tool handlers that format query results into text responses | `AppData`, `searchMatchesTool`, `teamRecordTool`, `compareTeamsTool`, `searchPlayersTool`, `competitionStandingsTool`, `datasetStatisticsTool`, `playerClubContextTool`, `listTeamCompetitionsTool` |
| src/types.ts | Core domain types | `Match`, `Player` |
| src/csv.ts | Quote-aware CSV parser to array of row records | `parseCSV()` |
| src/dates.ts | Flexible date parsing/formatting (ISO + Brazilian) and range check | `parseFlexibleDate()`, `formatISODate()`, `isWithinDateRange()` |
| src/normalize.ts | Team-name normalization, state-suffix handling, cross-dataset canonicalization | `stripAccents()`, `splitStateSuffix()`, `normalizeTeamName()`, `teamKey()`, `teamsMatch()`, `canonicalizeTeamNames()` |
| src/dataLoader.ts | Parses each of the 5 match CSVs + FIFA players CSV into domain objects | `parseBrasileiraoMatches()`, `parseCopaDoBrasilMatches()`, `parseLibertadoresMatches()`, `parseBRFootballDataset()`, `parseHistoricalBrasileirao()`, `parseFifaPlayers()`, `loadAllData()` |
| src/matchQueries.ts | Match search, head-to-head, cross-file deduplication | `findMatchesByTeam()`, `headToHead()`, `canonicalMatches()`, `MatchSearchOptions`, `HeadToHeadResult` |
| src/teamQueries.ts | Team win/draw/loss records and comparisons | `teamRecord()`, `compareTeams()`, `TeamRecord`, `TeamComparison` |
| src/playerQueries.ts | Player search/filter by name, club, nationality, position | `searchPlayersByName()`, `findPlayersByClub()`, `findPlayersByNationality()`, `topRatedPlayers()` |
| src/competitionQueries.ts | League standings computed from match results | `calculateStandings()`, `StandingsRow` |
| src/statsQueries.ts | Aggregate statistics (avg goals, win rates, biggest wins) | `averageGoalsPerMatch()`, `homeAwayWinRates()`, `biggestWins()` |
| tests/canonicalizeTeamNames.test.ts | Unit tests for team-name canonicalization | 7 tests |
| tests/competitionQueries.test.ts | Unit tests for standings calculation | 4 tests |
| tests/csv.test.ts | Unit tests for the CSV parser | 7 tests |
| tests/dataLoader.test.ts | Unit tests for per-CSV parsers and loader | 8 tests |
| tests/dates.test.ts | Unit tests for date parsing/formatting | 9 tests |
| tests/matchQueries.test.ts | Unit tests for match search and head-to-head | 10 tests |
| tests/normalize.test.ts | Unit tests for name normalization helpers | 12 tests |
| tests/playerQueries.test.ts | Unit tests for player queries | 11 tests |
| tests/server.test.ts | Tests server construction / tool registration | 3 tests |
| tests/statsQueries.test.ts | Unit tests for aggregate statistics | 5 tests |
| tests/teamQueries.test.ts | Unit tests for team records and comparisons | 5 tests |
| tests/tools.test.ts | Tests for tool handlers' text output | 15 tests |
