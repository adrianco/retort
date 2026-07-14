# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Executable entry point: resolve data dir, load CSVs into a DataStore, serve over MCP stdio | `main()` |
| src/server.ts | MCP server definition — registers the query tools, thin adapter over DataStore | `createSoccerServer(store)` |
| src/domain/types.ts | Canonical domain shapes independent of CSV formats | `Match`, `Player` |
| src/domain/normalize.ts | Team-name / date / text normalization for the messy source data | `cleanTeamName`, `teamKey`, `extractState`, `foldText`, `wordMatch`, `parseDate`, `parseGoals`, `deburr`, `stripBom` |
| src/data/loaders.ts | Per-file CSV loaders translating raw rows into `Match`/`Player` | `loadInto`, `loadDataset`, `loadBrasileirao`, `loadBrazilianCup`, `loadLibertadores`, `loadBrFootball`, `loadHistoricalBrasileirao`, `loadFifaPlayers` |
| src/data/store.ts | In-memory knowledge store: indexing, de-dup, and all query/aggregation logic | `DataStore` (`findMatches`, `teamRecord`, `headToHead`, `standings`, `competitionStatistics`, `findPlayers`) |
| tests/acceptance/harness.ts | Boots real server + real client over in-memory MCP transport | `startSystem()`, `TestSystem` |
| tests/acceptance/builders.ts | Test data builders for matches/players | `match()`, `player()` |
| tests/acceptance/*.test.ts | Acceptance suites driving the system through MCP tools only | 6 files, 29 tests |
| tests/unit/*.test.ts | Unit TDD for loaders + normalization internals | 2 files, 5 tests |
