# Modules

## Main (`src/main/java/br/soccer/`)

| Path | Purpose | Entry points |
|------|---------|--------------|
| McpServer.java | MCP server over stdio (newline-delimited JSON-RPC 2.0); registers and dispatches the 15 query tools | `main()`, `serve()`, `handle()`, `McpServer(QueryService)` |
| QueryService.java | All query logic over the in-memory data: matches, standings, rankings, players, cross-dataset views | `searchMatches`, `headToHead`, `teamStats`, `standings`, `teamRankings`, `matchStatistics`, `biggestWins`, `compareSeasons`, `derbies`, `knockoutStages`, `searchPlayers`, `playerDetails`, `playersByClub`, `clubProfile`, `datasetInfo`, `resolveTeams`, `findPlayers`, `Filter` |
| DataStore.java | Loads the six Kaggle CSVs into memory, merges duplicate fixtures across sources, labels cup finals | `load(Path)`, `defaultDir()`, `matches()`, `players()`, `teamKeys()`, `fileStats()`, `parseDate()` |
| TeamNames.java | Normalizes team names (accents, state suffixes, affixes, aliases) to one canonical key per club | `canonical()`, `fold()`, `display()` |
| Match.java | One merged match record with helpers for display and margins | `home()`, `away()`, `involves()`, `margin()`, `describe()` |
| Player.java | Record for a FIFA player database row | `Player` (record), `summary()` |
| Csv.java | Minimal RFC 4180 CSV reader (quotes, escaped quotes, embedded newlines, BOM) | `read(Path)`, `parse(String)` |
| Json.java | Hand-rolled JSON parser and writer for the JSON-RPC layer | `parse(String)`, `write(Object)` |

## Tests (`src/test/java/br/soccer/`)

| Path | Purpose | Entry points |
|------|---------|--------------|
| QueryServiceTest.java | Query logic coverage across all tools | 31 test methods |
| McpServerTest.java | JSON-RPC protocol handling (initialize, tools/list, tools/call, errors) | 5 test methods |
| NormalizationTest.java | Team-name canonicalization and display | 6 test methods |
| TestData.java | Shared fixture builder for the test suites | test helper (no `@Test`) |
