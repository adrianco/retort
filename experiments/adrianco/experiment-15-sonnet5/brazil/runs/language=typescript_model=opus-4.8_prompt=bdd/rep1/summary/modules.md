# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/index.ts | Entry point: load data, build server, serve over stdio | `main()` |
| src/server.ts | MCP server wiring — registers one tool per query capability | `createServer(store)` |
| src/dataStore.ts | Loads + normalizes all six CSV datasets into in-memory matches/players | `DataStore`, `defaultDataDir()`, `BRASILEIRAO` |
| src/csv.ts | Synchronous CSV loader (BOM strip, quoted fields, UTF-8) | `loadCsv()`, `CsvRow` |
| src/normalize.ts | Team-name/date/goal normalization + lenient matching helpers | `cleanTeamName`, `teamKey`, `teamIdentityKey`, `teamMatches`, `parseDate`, `parseGoals` |
| src/types.ts | Shared domain types | `Match`, `Player`, `TeamRecord`, `StandingsRow`, `Competition` |
| src/format.ts | Human-readable formatting of query results into MCP text output | 11 `format*` functions |
| src/queries/filters.ts | Reusable match-filtering primitives | `filterMatches`, `competitionMatches`, `sortByDate`, `MatchFilter` |
| src/queries/matches.ts | Find matches, head-to-head, last meeting | `findMatches`, `headToHead`, `lastMeeting`, `orientGoals` |
| src/queries/teams.ts | Team W/D/L record, goals, home/away split | `teamStats`, `TeamStats` |
| src/queries/players.ts | FIFA player search/filter/rank + club summaries | `filterPlayers`, `rankByOverall`, `searchPlayersByName`, `summarizeByClub` |
| src/queries/competitions.ts | Calculated league standings + champion | `calculateStandings`, `brasileiraoStandings`, `brasileiraoChampion` |
| src/queries/stats.ts | Aggregate stats, biggest wins, top scorers | `aggregateStats`, `biggestWins`, `topScoringTeams` |
| tests/fixtures.ts | Shared fixtures — real DataStore + synthetic match/player builders | `realStore()`, `makeMatch()`, `makePlayer()` |
| tests/matches.test.ts | Match query scenarios | 6 tests |
| tests/teams.test.ts | Team record scenarios | 3 tests |
| tests/players.test.ts | Player search/filter scenarios | 6 tests |
| tests/competitions.test.ts | Standings/champion scenarios | 4 tests |
| tests/stats.test.ts | Aggregate stats scenarios | 5 tests |
| tests/normalize.test.ts | Name/date/goal normalization edge cases | 15 tests |
| tests/server.test.ts | End-to-end MCP client/server over in-memory transport | 6 tests |
