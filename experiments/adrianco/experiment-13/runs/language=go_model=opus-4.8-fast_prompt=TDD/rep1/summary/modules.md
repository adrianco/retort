# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Program entry point and stdio transport loop | `main()`, `(*Server).Serve()`, `resolveDataDir()` |
| mcp.go | MCP JSON-RPC 2.0 server core — dispatcher + protocol handlers | `NewServer()`, `(*Server).Dispatch()` |
| models.go | Core in-memory data model (Match, Player, Dataset) | `Match`, `Player`, `Dataset`, `(Match).Winner()`, `(Match).Involves()` |
| loader.go | CSV ingestion — per-file loaders for 5 match files + FIFA players | `LoadDataset()` |
| normalize.go | Team-name normalization and multi-format date parsing | `NormalizeTeam()`, `TeamsMatch()`, `ParseDate()` |
| query.go | Query engine — match search, team records, H2H, standings, player search, stats | `(*Dataset).FindMatches()`, `(*Dataset).TeamRecord()`, `(*Dataset).HeadToHead()`, `(*Dataset).Standings()`, `(*Dataset).SearchPlayers()`, `(*Dataset).Stats()`, `(*Dataset).BiggestWins()` |
| tools.go | MCP tool catalog — 6 tools with JSON-Schema and handler functions | `Tools()` |
| format.go | Human-readable rendering of query results | `FormatMatches()`, `FormatRecord()`, `FormatH2H()`, `FormatStandings()`, `FormatPlayers()`, `FormatStats()` |
| loader_test.go | Tests CSV loading: row counts, field parsing, player data | 3 test functions |
| normalize_test.go | Tests team normalization and date parsing | 3 test functions |
| query_test.go | Behavioral tests for query engine against ground-truth data | 11 test functions |
| mcp_test.go | Tests MCP protocol: initialize, tools/list, tools/call, errors | 12 test functions |
| serve_test.go | Integration test for stdio JSON-RPC transport | 1 test function |
