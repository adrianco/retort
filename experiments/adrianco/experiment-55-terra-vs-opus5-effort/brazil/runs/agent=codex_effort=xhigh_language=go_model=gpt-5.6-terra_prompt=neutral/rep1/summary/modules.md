# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entrypoint: parse `-data-dir`, load CSVs, run stdio server | `main()` |
| server.go | MCP JSON-RPC/stdio transport, tool registry, dispatch | `Server`, `NewServer()`, `RunServer()`, `HandleRequest()`, `toolDefinitions()` |
| loader.go | CSV parsing for 5 match files + FIFA players into a `DataStore` | `LoadData()`, `parseDate()` |
| query.go | Query/aggregation logic over matches and players | `SearchMatches`, `TeamStatistics`, `HeadToHead`, `SearchPlayers`, `Standings`, `TeamRankings`, `CompetitionStatistics`, `BiggestWins`, `Derbies`, `TeamCompetitions` |
| normalize.go | Accent/case folding + team/competition/nationality canonicalization | `canonicalText`, `canonicalTeam`, `canonicalCompetition`, `canonicalNationality` |
| types.go | Shared structs: `Match`, `Player`, `DataStore`, `MatchFilter`, result types | `Match`, `Player`, `DataStore`, `MatchFilter`, `TeamStatistics`, `HeadToHead`, `Standing` |
| server_test.go | Unit + integration tests (fixtures + bundled dataset) | 4 test functions |
