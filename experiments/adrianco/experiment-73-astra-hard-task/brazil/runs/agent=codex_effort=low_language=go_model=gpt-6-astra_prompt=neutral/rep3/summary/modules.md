# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | MCP stdio JSON-RPC server, tool registry, tool dispatch | `main()`, `Serve()`, `toolList()`, `(*Store).Call()` |
| data.go | CSV loading, team-name normalization, cross-source dedup, cup-stage inference | `LoadStore()`, `NormalizeTeam()`, `matchFromRow()`, types `Store`/`Match`/`Player` |
| query.go | Query/filter engine, aggregates, standings, player search, knowledge graph | `(*Store).FindMatches/TeamStats/Standings/Statistics/FindPlayers/Graph`, `Filter`, `Record` |
| soccer_test.go | Unit + integration tests over the real datasets | 10 `Test*` funcs, 2 `Benchmark*`, `TestTwentySampleQuestions` (20 subtests) |

Stdlib only — no `go.sum`, no third-party dependencies.
