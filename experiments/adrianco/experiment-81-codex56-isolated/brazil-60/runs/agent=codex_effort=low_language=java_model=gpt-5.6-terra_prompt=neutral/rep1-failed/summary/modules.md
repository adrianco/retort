# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main/java/org/brazilsoccer/mcp/BrazilianSoccerMcpServer.java | MCP stdio server: JSON-RPC loop, tool registry, dispatch | `main()`, `response()`, `call()`, `tools()` |
| src/main/java/org/brazilsoccer/mcp/SoccerService.java | Query/aggregation operations over the repository | `matches()`, `teamStatistics()`, `headToHead()`, `standings()`, `competitionStatistics()` |
| src/main/java/org/brazilsoccer/mcp/SoccerRepository.java | In-memory read-only view loaded from the CSVs | `load()`, `findMatches()`, `findPlayers()`, `matches()` |
| src/main/java/org/brazilsoccer/mcp/Match.java | Match record type | `Match` (record), `involves()` |
| src/main/java/org/brazilsoccer/mcp/Names.java | Team-name normalization (accents, state suffixes) | `normalize()`, `same()` |
| src/main/java/org/brazilsoccer/mcp/Csv.java | RFC-4180-ish CSV reader (UTF-8, quoted commas) | `read()` |
| src/main/java/org/brazilsoccer/mcp/Json.java | Minimal JSON parser/writer for JSON-RPC envelopes | `parse()`, `write()` |
| src/test/java/org/brazilsoccer/mcp/SoccerRepositoryTest.java | JUnit 5 suite exercising load + query functions | 6 test methods |
