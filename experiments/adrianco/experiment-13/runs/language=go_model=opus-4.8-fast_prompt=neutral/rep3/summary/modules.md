# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entrypoint: loads CSVs, builds server, serves MCP over stdio | `main()` |
| internal/mcp/jsonrpc.go | JSON-RPC 2.0 wire types + error codes (stdlib only) | `request`, `response`, `rpcError`, `newError` |
| internal/mcp/server.go | stdio transport loop + method dispatch (initialize/tools.list/tools.call/ping) | `Server`, `NewServer`, `Serve`, `Dispatch`, `CallTool` |
| internal/mcp/tools.go | Registers the 7 MCP tools; arg parsing + answer formatting | `registerTools` (private) |
| internal/soccer/model.go | Core graph types + canonical competition names | `Match`, `Player`, `DB`, `TeamCount`, `Competitions` |
| internal/soccer/load.go | Reads the 6 Kaggle CSVs, dedups by source coverage, resolves teams | `Load`, per-file loaders |
| internal/soccer/normalize.go | Team/competition name normalization (accents, suffixes) | `TeamKey`, `CleanTeamName`, `NormalizeCompetition` |
| internal/soccer/query.go | Query engine: search, H2H, records, standings, players, stats | `FindMatches`, `HeadToHead`, `TeamRecord`, `Standings`, `SearchPlayers`, `CompetitionStats` |
| internal/soccer/format.go | Renders query results as human-readable text answers | `FormatMatches`, `FormatH2H`, `FormatRecord`, `FormatStandings`, `FormatPlayers`, `FormatStats` |
| internal/soccer/normalize_test.go | Unit tests for name/competition normalization | 6 test functions |
| internal/soccer/engine_test.go | Unit tests for load + query engine (synthetic data) | 8 test functions |
| internal/soccer/integration_test.go | Integration test against bundled Kaggle data | `TestRealData` |
| internal/mcp/server_test.go | MCP protocol + stdio round-trip tests | 8 test functions |
