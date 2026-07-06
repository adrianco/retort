# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | stdio entry point; wires server to `StdioServerTransport` | `main()` |
| src/server.ts | Registers 12 MCP tools and formats text responses | `createServer()` |
| src/dataLoader.ts | Loads/parses all 6 CSVs into an in-memory `Dataset`, with cross-dataset dedup | `getDataset()` |
| src/normalize.ts | Team-name normalization (state-suffix, accent/case folding) and flexible date parsing | `parseTeamName()`, `teamKeyMatchesQuery()`, `parseFlexibleDate()`, `normalizeKey()`, `formatDate()`, `stripDiacritics()` |
| src/types.ts | Shared `Match`/`Player`/`Dataset`/`TeamKey` types | `Match`, `Player`, `Dataset`, `TeamKey`, `Competition` |
| src/queries/matchQueries.ts | Match filtering + head-to-head + line formatting | `findMatches()`, `headToHead()`, `formatMatchLine()` |
| src/queries/teamQueries.ts | Team W/L/D record and competition membership | `teamRecord()`, `teamCompetitions()` |
| src/queries/competitionQueries.ts | Standings computed from matches; competition catalog | `standings()`, `listCompetitions()` |
| src/queries/statsQueries.ts | Aggregate stats: average goals, biggest wins, best venue record | `averageGoals()`, `biggestWins()`, `bestVenueRecord()` |
| src/queries/playerQueries.ts | FIFA player search and club breakdowns | `searchPlayers()`, `playersByClub()`, `brazilianPlayersByClub()` |
| src/queries/shared.ts | Shared filter/sort helpers and table-row accumulator | `competitionMatches()`, `byDateDesc()`, `getOrCreateRow()`, `DEFAULT_LIMIT` |
| test/normalize.test.ts | Unit tests for name/date normalization | 15 tests |
| test/matchQueries.test.ts | Match filter + head-to-head tests | 9 tests |
| test/dataLoader.test.ts | CSV loading + dedup tests | 7 tests |
| test/playerQueries.test.ts | Player search/club tests | 6 tests |
| test/teamQueries.test.ts | Team record tests | 5 tests |
| test/statsQueries.test.ts | Aggregate stats tests | 4 tests |
| test/competitionQueries.test.ts | Standings tests | 3 tests |
