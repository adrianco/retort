# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entrypoint; loads data, runs MCP stdio server or a one-shot `--query` | `main`, `defaultDataDir()` |
| server.go | MCP JSON-RPC-over-stdio transport, tool/resource/prompt definitions, natural-language router, response formatting | `MCPServer`, `NewMCPServer`, `Run`, `HandleRequest`, `CallTool`, `toolDefinitions` |
| data.go | CSV loading of all six datasets, normalization into `Match`/`Player`, filtering, dedup, source selection | `DataStore`, `LoadData`, `SearchMatches`, `DisplayTeam` |
| query.go | Calculated analytics over matches/players | `TeamStatistics`, `HeadToHead`, `Standings`, `CompetitionStatistics`, `BestTeamRecord`, `MostGoalsScorer`, `SearchPlayers`, `TeamCompetitions`, `CompareSeasons` |
| model.go | Domain types and filter structs | `Match`, `Player`, `MatchFilter`, `PlayerFilter`, `TeamStatistics`, `HeadToHeadRecord`, `Standing`, `CompetitionSummary` |
| normalize.go | Accent/state-suffix/alias normalization for team, competition, and text matching | `normalizeText`, `normalizeTeam`, `normalizeCompetition`, `teamNameMatches`, `teamAliases` |
| mcp_test.go | Integration + unit tests exercising loading, queries, standings, players, NL routing, JSON-RPC transport | 10 test functions (`TestMain` + 9 `TestFeature*`/unit) |
