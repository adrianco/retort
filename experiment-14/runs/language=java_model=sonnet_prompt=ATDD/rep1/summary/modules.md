# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/soccer/mcp/BrazilianSoccerMcpServer.java | MCP server; wires services and exposes 6 query tools | `findMatches`, `getTeamStats`, `findPlayers`, `getStandings`, `getHeadToHead`, `getStatistics`, `startMcpServer`, `main` |
| src/main/java/com/soccer/mcp/service/DataLoader.java | Loads 5 match CSVs + FIFA player CSV into model lists | `loadAllMatches()`, `loadPlayers()` |
| src/main/java/com/soccer/mcp/service/MatchService.java | Match filtering, standings, head-to-head, aggregate stats | `findMatches()`, `getTeamStats()`, `getStandings()`, `getHeadToHead()`, `getStatistics()` |
| src/main/java/com/soccer/mcp/service/PlayerService.java | Player filtering by name/nationality/club/position/rating | `findPlayers()` |
| src/main/java/com/soccer/mcp/service/TeamNameNormalizer.java | Normalizes team names (state suffixes, accents, aliases) | `normalize()`, `canonical()`, `matches()` |
| src/main/java/com/soccer/mcp/model/Match.java | Match record | `Match`, getters |
| src/main/java/com/soccer/mcp/model/Player.java | Player record | `Player`, getters |
| src/main/java/com/soccer/mcp/model/TeamStats.java | W/L/D + goals aggregate | `TeamStats`, `addMatch()`, `getPoints()` |
| src/main/java/com/soccer/mcp/model/Standing.java | Position + TeamStats pair | `Standing` |
| src/test/java/com/soccer/mcp/acceptance/MatchQueriesAcceptanceTest.java | Acceptance tests for match queries (public API only) | 9 tests |
| src/test/java/com/soccer/mcp/acceptance/PlayerQueriesAcceptanceTest.java | Acceptance tests for player queries | 8 tests |
| src/test/java/com/soccer/mcp/acceptance/TeamQueriesAcceptanceTest.java | Acceptance tests for team stats | 6 tests |
| src/test/java/com/soccer/mcp/acceptance/CompetitionQueriesAcceptanceTest.java | Acceptance tests for standings | 7 tests |
| src/test/java/com/soccer/mcp/acceptance/StatisticsAcceptanceTest.java | Acceptance tests for head-to-head + aggregate stats | 9 tests |
| src/test/java/com/soccer/mcp/unit/TeamNameNormalizerTest.java | Unit TDD for the normalizer | 12 tests |
