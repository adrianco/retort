# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/server.ts | MCP stdio server; registers 18 soccer query tools | `createServer()`, module main (`StdioServerTransport`) |
| src/queries.ts | All query/aggregation logic over the dataset, formatted as text | `searchMatches`, `headToHead`, `teamRecord`, `standings`, `champion`, `relegated`, `competitionStats`, `compareSeasons`, `biggestWins`, `rankTeams`, `teamCompetitions`, `derbies`, `searchPlayers`, `playerDetails`, `brazilianClubsSummary`, `teamProfile`, `datasetInfo` |
| src/data.ts | Loads all 6 Kaggle CSVs into normalized Match/Player structures; dedup + cache | `loadDataset()`, `getDataset()`, `Match`, `Player`, `Dataset` |
| src/normalize.ts | Team-name canonicalization (aliases, state suffixes) and date parsing | `teamKey`, `displayName`, `teamMatches`, `parseDate`, `stripAccents` |
| src/csv.ts | Minimal RFC-4180 CSV parser (quotes, embedded commas, BOM) | `parseCsv()` |
| test/queries.test.ts | 31 tests: parser/normalization units + Q1–Q24 sample-question cases | 31 `test()` functions |
| test/server.test.ts | MCP round-trip test via in-memory transport | 1 `test()` function |
