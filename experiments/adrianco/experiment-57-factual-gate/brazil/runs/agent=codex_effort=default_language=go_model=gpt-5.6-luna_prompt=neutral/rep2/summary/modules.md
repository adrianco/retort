# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Program entry: loads the store, serves JSON-RPC over stdin/stdout | `main()` |
| server.go | MCP JSON-RPC server: tool definitions, dispatch, request loop | `Serve()`, `toolDefinitions()`, `callTool()`, `dataDir()` |
| soccer.go | CSV loading, in-memory store, and all query/aggregation logic | `Store`, `Match`, `Player`, `LoadStore()`, `SearchMatches()`, `Stats()`, `SearchPlayers()`, `Average()`, `Standings()`, `HeadToHead()` |
| soccer_test.go | Unit tests for query logic, dedup, and MCP protocol | 5 test functions (`TestSearchAndStats`, `TestPlayersAndAverage`, `TestHeadToHead`, `TestLoadStoreDeduplicatesOverlappingFixtures`, `TestMCPProtocol`) |
| go.mod | Module definition (`brazilian-soccer-mcp`, go 1.23), no external deps | — |
