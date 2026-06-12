# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entrypoint: loads datasets, starts MCP server on stdio | `main()` |
| internal/mcp/server.go | JSON-RPC 2.0 / MCP server: framing, dispatch, tool-call handling | `Server`, `New()`, `(*Server).Serve()` |
| internal/mcp/tools.go | Tool definitions (schemas) + handlers wiring args to soccer queries | `toolDefinitions()`, `toolArgs`, `(*Server).toolSearchMatches/…` |
| internal/mcp/format.go | Human-readable rendering of matches/standings | `formatMatch()`, `writeMatchList()` |
| internal/soccer/model.go | Core domain types | `Match`, `Player`, `KB` |
| internal/soccer/load.go | CSV ingestion for 5 match datasets + FIFA players | `LoadDir()` |
| internal/soccer/parse.go | Date and integer parsing helpers | `ParseDate()`, `parseInt()` |
| internal/soccer/normalize.go | Accent/convention-insensitive team-name matching | `NormalizeTeam()`, `TeamsMatch()` |
| internal/soccer/query.go | Match filtering/search | `MatchFilter`, `(*KB).SearchMatches()` |
| internal/soccer/players.go | Player filtering/search | `PlayerFilter`, `(*KB).SearchPlayers()` |
| internal/soccer/competition.go | Standings, dedup across overlapping datasets, aggregate/biggest-win stats | `(*KB).Standings()`, `(*KB).CompetitionStats()`, `(*KB).BiggestWins()`, `(*KB).DedupedMatches()` |
| internal/soccer/stats.go | Team record + head-to-head aggregation | `TeamRecord`, `(*KB).TeamRecord()`, `(*KB).HeadToHead()` |
| internal/mcp/*_test.go | MCP protocol + tool tests | serve_test (1), server_test (7), tools_test (9) |
| internal/soccer/*_test.go | Unit + integration tests over the soccer engine | parse, normalize, load, query, players, competition, dedup, stats, query_integration |

Implementation: 12 `.go` files (~1,594 LOC). Tests: 13 `_test.go` files (~1,008 LOC), 50 test functions. Zero external dependencies (Go stdlib only).
