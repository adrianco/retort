# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/com/brasileirao/mcp/server/Main.java | Process entry point; resolves data dir, loads graph, starts stdio server (`--selftest` flag) | `main(String[])`, `resolveDataDir(String)` |
| src/main/java/com/brasileirao/mcp/server/McpServer.java | JSON-RPC 2.0 over stdio MCP transport (initialize, tools/list, tools/call, ping) | `McpServer(...)`, `serve(InputStream, OutputStream)`, `handleMessage(JsonNode)` |
| src/main/java/com/brasileirao/mcp/server/Tools.java | MCP tool catalogue + dispatcher; formats query results as text | `Tools(QueryService)`, `listTools()`, `callTool(String, JsonNode)` |
| src/main/java/com/brasileirao/mcp/query/QueryService.java | Analytics layer over the graph: match/team/player/standings/stats queries | `searchMatches`, `headToHead`, `teamRecord`, `searchPlayers`, `standings`, `averageGoals`, `biggestWins`, `bestRecords`, `resolveCompetition`; records `MatchQuery`, `PlayerQuery`, `TeamRecord`, `HeadToHead`, `StandingRow`, `GoalStats`, enum `Scope` |
| src/main/java/com/brasileirao/mcp/data/KnowledgeGraph.java | Loads 6 Kaggle CSVs into unified Match/Player collections with indexes | `load(Path)`, `matchesForTeam`, `playersForClub`, `playersForNationality`, `competitions`, `parseDate(String)` |
| src/main/java/com/brasileirao/mcp/model/Match.java | Immutable unified match value object | `Match(...)`, `involves`, `winner`, `hasResult`, `describe` |
| src/main/java/com/brasileirao/mcp/model/Player.java | Immutable FIFA player value object | `Player(...)`, accessors, `describe` |
| src/main/java/com/brasileirao/mcp/util/TeamNames.java | Canonicalizes club-name spelling variants across datasets | `canonical(String)`, `display(String)`, `sameTeam`, `stripAccents` |
| src/main/java/com/brasileirao/mcp/util/CsvReader.java | Dependency-free RFC-4180 streaming CSV parser (UTF-8, BOM, quotes) | `parse(Path, Consumer)`, `parse(InputStream, Consumer)` |
| src/test/java/com/brasileirao/mcp/KnowledgeGraphTest.java | Graph loading/indexing tests | 5 test methods |
| src/test/java/com/brasileirao/mcp/QueryServiceTest.java | Query/analytics tests | 14 test methods |
| src/test/java/com/brasileirao/mcp/McpServerTest.java | JSON-RPC protocol handling tests | 8 test methods |
| src/test/java/com/brasileirao/mcp/TeamNamesTest.java | Name-canonicalization tests | 8 test methods |
| src/test/java/com/brasileirao/mcp/TestData.java | Shared in-memory test fixtures | (helper, no tests) |
