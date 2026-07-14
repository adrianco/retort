# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entrypoint; loads data dir and serves MCP stdio | `main()` |
| mcp/server.go | MCP server: tool dispatch, JSON-RPC stdio loop, tool schemas | `Server`, `NewServer()`, `Call()`, `ServeStdio()` |
| internal/loader/loader.go | CSV loaders for 5 match files + FIFA players; team-name normalization, multi-format date parsing | `Load()`, `Dataset`, `Match`, `Player`, `NormalizeTeam()` |
| internal/query/query.go | Query/aggregation engine: match search, team stats, player search, standings, statistics, head-to-head | `FindMatches()`, `GetTeamStats()`, `FindPlayers()`, `GetStandings()`, `GetStatistics()` |
| acceptance_test.go | Black-box acceptance suite exercising the server via `Call` | 15 test functions (AC1–AC15) |
