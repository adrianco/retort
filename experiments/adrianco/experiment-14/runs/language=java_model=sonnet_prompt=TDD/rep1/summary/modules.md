# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/braziliansoccer/mcp/BrazilianSoccerMcpServer.java | MCP stdio server; loads data, wires services, registers 6 query tools | `main()`, `build*Tool()` |
| src/main/java/com/braziliansoccer/mcp/loader/MatchLoader.java | Parses the 5 match CSVs into `Match`, normalizing team names | `loadAll()` |
| src/main/java/com/braziliansoccer/mcp/loader/PlayerLoader.java | Parses `fifa_data.csv` (with BOM strip) into `Player` | `loadAll()` |
| src/main/java/com/braziliansoccer/mcp/model/Match.java | Match record | `Match` (record) |
| src/main/java/com/braziliansoccer/mcp/model/Player.java | Player record | `Player` (record) |
| src/main/java/com/braziliansoccer/mcp/service/MatchService.java | Match filtering by team/competition/season | `findByTeam`, `findByCompetition`, `findBySeason` |
| src/main/java/com/braziliansoccer/mcp/service/PlayerService.java | Player search by name/nationality/club + top-N | `findByName`, `findByNationality`, `findByClub`, `getTopPlayers` |
| src/main/java/com/braziliansoccer/mcp/service/StatisticsService.java | Aggregates: team record, H2H, standings, biggest wins, avg goals | `getTeamRecord`, `getHeadToHead`, `getStandings`, `getBiggestWins` |
| src/main/java/com/braziliansoccer/mcp/service/TeamNameNormalizer.java | Strips state suffixes (`-SP`) and does case-insensitive contains matching | `normalize`, `matches` |
| src/test/java/.../loader/MatchLoaderTest.java | Loader tests | 4 test methods |
| src/test/java/.../loader/PlayerLoaderTest.java | Loader tests | 4 test methods |
| src/test/java/.../service/MatchServiceTest.java | Match query tests | 5 test methods |
| src/test/java/.../service/PlayerServiceTest.java | Player query tests | 5 test methods |
| src/test/java/.../service/StatisticsServiceTest.java | Stats/standings/H2H tests | 5 test methods |
| src/test/java/.../service/TeamNameNormalizerTest.java | Normalizer tests | 4 test methods |
