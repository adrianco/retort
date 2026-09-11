# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | MCP server over stdio JSON-RPC 2.0; tool schema, request loop, CLI entry | `main()`, `Serve()`, `toolList()` |
| data.go | CSV loading, team-name/date normalization, cross-source match dedup | `Load()`, `team()`, `competition()`, `parseDate()`, `score()`; types `Match`, `Player`, `Graph` |
| query.go | Query engine: filtering, aggregation, standings, head-to-head, stats | `Graph.Query()`, `Graph.matches()`, `Graph.players()`, `records()`; types `Filter`, `Record` |
| soccer_test.go | Unit + integration tests against fixtures and the real datasets | 7 test functions |

Stdlib only — `go.mod` declares no external dependencies (no `go.sum`).
