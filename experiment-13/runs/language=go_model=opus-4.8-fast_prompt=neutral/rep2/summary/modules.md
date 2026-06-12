# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Executable entry: resolves data dir, loads CSVs, wires MCP server, runs stdio loop | `main()` |
| internal/mcp/protocol.go | JSON-RPC 2.0 wire types + serve/dispatch/write loop | `Server`, `NewServer`, `Tool`, `Request`, `Response` |
| internal/mcp/dispatch.go | Maps MCP methods (initialize, tools/list, tools/call, ping) to handlers | `(*Server).dispatch` |
| internal/server/tools.go | MCP tool catalog: 8 tools bound to the soccer DB | `Build()`, `Tools()` |
| internal/server/args.go | Tolerant arg coercion from JSON-RPC params | `argString`, `argInt`, `argBool` |
| internal/server/format.go | Human-readable formatting of matches/players/records | `formatMatchList`, `formatPlayer`, `formatRecord` |
| internal/soccer/loader.go | CSV ingestion of all 6 datasets, dedup, alias building | `Load()`, `DB` |
| internal/soccer/query.go | Pure query/aggregation layer over the DB | `SearchMatches`, `TeamRecord`, `HeadToHead`, `Standings`, `Statistics`, `SearchPlayers`, `PlayersByClub`, `Competitions` |
| internal/soccer/model.go | Domain structs + competition constants | `Match`, `Player`, `(Match).Winner` |
| internal/soccer/normalize.go | Team-name normalization, accent folding, match keys | `teamKey`, `matchKey`, `cleanTeamName`, `suffixState` |
| internal/soccer/soccer_test.go | Unit tests for loader/query/normalize | 10 test functions |
| internal/server/server_test.go | Unit tests for the MCP tool catalog | 11 test functions |
| internal/mcp/mcp_test.go | Protocol-level tests (initialize/list/call/errors) | 6 test functions |
| integration_test.go | End-to-end test against real Kaggle data (2019 table) | 1 test function (conditional skip) |
