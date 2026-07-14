# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | MCP server entrypoint; registers 9 tools and dispatches calls over stdio | `main()`, request handlers for `ListTools`/`CallTool` |
| src/data-loader.ts | Loads and normalizes the 6 Kaggle CSVs into an in-memory `DataStore` | `loadAllData()`, `normalizeTeamName()`, `load*Matches()`, `loadFifaPlayers()` |
| src/query-engine.ts | Pure query/aggregation functions over the `DataStore` | `queryMatches()`, `getTeamStats()`, `getHeadToHead()`, `getStandings()`, `queryPlayers()`, `getBiggestWins()`, `getLeagueStats()`, `getTopScoringTeams()` |
| src/index.test.ts | Jest suite exercising loaders, queries, stats, and sample questions | 46 tests across 9 `describe` blocks |
