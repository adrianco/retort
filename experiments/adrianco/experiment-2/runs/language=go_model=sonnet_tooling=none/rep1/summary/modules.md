# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Entry point: loads CSVs from data dir, starts MCP server over stdio | `main()` |
| data.go | Match/Player structs, CSV loaders for all 6 datasets, in-memory `Database` | `Database`, `Match`, `Player`, `NewDatabase()`, `(*Database).LoadAll()` |
| server.go | MCP JSON-RPC 2.0 server over stdio (Content-Length + newline framing) | `MCPServer`, `NewMCPServer()`, `(*MCPServer).Serve()`, `handleRequest` |
| tools.go | 6 MCP tool definitions + query handlers + dispatch | `GetToolDefinitions()`, `SearchMatches`, `GetTeamStats`, `SearchPlayers`, `GetStandings`, `GetHeadToHead`, `GetBiggestWins`, `DispatchTool` |
| normalize.go | Team-name normalization, date/goal/season parsing, small utils | `normalizeTeamName`, `teamMatches`, `parseDate`, `parseGoals`, `parseSeason` |
| mcp_test.go | BDD-style tests for queries, stats, players, standings, H2H, normalize | 29 `Test*` functions |
