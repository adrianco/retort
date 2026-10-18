# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/brazilsoccer/Main.java | Process entry; loads data, starts MCP server on stdio | `main()` |
| src/main/java/com/brazilsoccer/mcp/McpServer.java | JSON-RPC 2.0 MCP server (initialize, ping, tools/list, tools/call) | `McpServer`, `serve()`, `handle()` |
| src/main/java/com/brazilsoccer/mcp/SoccerTools.java | Tool definitions + dispatch; formats query results as text | `SoccerTools`, `definitions()`, `call()` |
| src/main/java/com/brazilsoccer/query/SoccerQueries.java | Read-only queries over the repository (matches, records, h2h, standings, stats) | `SoccerQueries`, `MatchFilter`, `PlayerFilter`, `HeadToHead`, `LeagueStats`, `Venue` |
| src/main/java/com/brazilsoccer/query/TeamTally.java | Running W/D/L and goal totals for one team | `TeamTally`, `addResult()`, `points()`, `winRate()` |
| src/main/java/com/brazilsoccer/data/DataRepository.java | In-memory match/player store with cross-source de-duplication | `DataRepository`, `load()`, `dedupe()` |
| src/main/java/com/brazilsoccer/data/DataLoader.java | Converts each of the 6 Kaggle CSVs into Match/Player records; date parsing | `loadBrasileirao()`, `loadHistorical()`, `loadCup()`, `loadLibertadores()`, `loadExtended()`, `loadPlayers()`, `parseDate()` |
| src/main/java/com/brazilsoccer/data/Csv.java | Minimal CSV reader returning header-keyed records | `Csv`, `readRecords()` |
| src/main/java/com/brazilsoccer/data/TeamNames.java | Normalizes team names across sources (accents, state suffixes, aliases) | `TeamNames`, `normalize()`, `key()`, `matches()`, `displayName()` |
| src/main/java/com/brazilsoccer/data/Match.java | Fixture record (date, competition, teams, goals) | `Match`, `season()`, `hasResult()` |
| src/main/java/com/brazilsoccer/data/Player.java | FIFA player record | `Player` |
| src/test/java/com/brazilsoccer/mcp/McpServerTest.java | MCP protocol tests | 9 test methods |
| src/test/java/com/brazilsoccer/query/SoccerQueriesTest.java | Query-capability tests incl. real-dataset checks | 12 test methods |
| src/test/java/com/brazilsoccer/data/DataLoaderTest.java | CSV-to-record / date-parse tests | 4 test methods |
| src/test/java/com/brazilsoccer/data/DataRepositoryTest.java | Load + de-duplication tests | 4 test methods |
| src/test/java/com/brazilsoccer/data/TeamNamesTest.java | Name-normalization tests | 6 test methods |
| src/test/java/com/brazilsoccer/data/CsvTest.java | CSV parsing tests | 5 test methods |
| src/test/java/com/brazilsoccer/TestFixtures.java | Shared test match/player builders | (helpers, no @Test) |
