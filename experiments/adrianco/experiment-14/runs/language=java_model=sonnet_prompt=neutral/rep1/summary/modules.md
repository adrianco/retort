# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/braziliansoccer/mcp/McpServer.java | MCP server over stdio: reads JSON-RPC requests, dispatches `tools/list` + `tools/call`, registers 9 tools | `McpServer`, `run()`, `main()` |
| src/main/java/com/braziliansoccer/mcp/tools/MatchTools.java | Match/team query tools backed by loaded matches | `searchMatches`, `headToHead`, `teamStats`, `standings`, `matchStatistics` |
| src/main/java/com/braziliansoccer/mcp/tools/PlayerTools.java | Player query tools backed by FIFA data | `searchPlayers`, `playerProfile`, `teamPlayers`, `topPlayersByNationality` |
| src/main/java/com/braziliansoccer/mcp/data/DataLoader.java | Loads all 6 CSVs into in-memory lists via OpenCSV | `DataLoader(dir)`, `load()`, `getAllMatches()`, `getAllPlayers()` |
| src/main/java/com/braziliansoccer/mcp/data/TeamNormalizer.java | Normalizes team names (strips state suffix, accents) for matching | `normalize()`, `matches()` |
| src/main/java/com/braziliansoccer/mcp/data/Match.java | Match record + team-involvement helpers | `Match`, `involvesTeam()`, `involvesTeams()` |
| src/main/java/com/braziliansoccer/mcp/data/Player.java | FIFA player record | `Player` (public fields) |
| src/test/java/com/braziliansoccer/mcp/McpServerProtocolTest.java | JSON-RPC protocol tests | 9 test methods |
| src/test/java/com/braziliansoccer/mcp/MatchToolsTest.java | Match/team tool tests | 15 test methods |
| src/test/java/com/braziliansoccer/mcp/PlayerToolsTest.java | Player tool tests | 15 test methods |
| src/test/java/com/braziliansoccer/mcp/DataLoaderTest.java | CSV loading tests | 10 test methods |
| src/test/java/com/braziliansoccer/mcp/TeamNormalizerTest.java | Name-normalization tests | 12 test methods |
