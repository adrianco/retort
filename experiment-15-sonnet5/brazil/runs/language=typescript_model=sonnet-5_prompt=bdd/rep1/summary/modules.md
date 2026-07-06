# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Stdio entrypoint; loads store, starts MCP server | `main()` |
| src/server.ts | Builds MCP server, registers 14 tools | `createServer(store)` |
| src/types.ts | Shared types (Match, Player, TeamRecord, StandingsRow, Competition) | type exports |
| src/data/loader.ts | Reads/parses CSV files (BOM-aware) | `loadCsv()` |
| src/data/store.ts | In-memory knowledge store over 6 CSVs; dedup + indices | `SoccerDataStore`, `.load()` |
| src/data/normalize.ts | Team-name normalization, alias table, flexible date parsing | `normalizeTeamName()`, `parseFlexibleDate()`, `formatDate()` |
| src/queries/matches.ts | Match search, head-to-head, most-recent | `searchMatches()`, `headToHead()`, `mostRecentMatch()` |
| src/queries/teams.ts | Team records, rankings, competitions-for-team | `getTeamRecord()`, `rankTeamsByRecord()`, `competitionsForTeam()` |
| src/queries/players.ts | Player search + Brazilian-club grouping | `searchPlayers()`, `brazilianPlayersAtBrazilianClubs()`, `topBrazilianPlayers()` |
| src/queries/competitions.ts | Standings/relegation calculated from matches | `calculateStandings()`, `bottomOfTable()`, `seasonsForCompetition()` |
| src/queries/stats.ts | Aggregate goal/outcome stats, biggest wins | `calculateGoalStats()`, `biggestWins()` |
| src/queries/helpers.ts | Shared match filtering/record helpers | `filterMatches()`, `computeTeamRecord()`, `resultForTeam()` |
| tests/*.test.ts | 65 BDD-style vitest specs across 8 files | see interfaces.md |
| tests/support/testStore.ts | Shared test fixture builder | `buildTestStore()` |

12 source modules, 8 test files, 1 test-support module.
