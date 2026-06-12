# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Entry point: loads data, registers tools, serves MCP over stdio | `main()` |
| embed.go | Compile-time embedding of the six Kaggle CSVs | `dataFS()`, `embeddedData` |
| tools.go | Registers the 7 MCP tools, decodes/validates args, renders results | `registerTools()`, `args`, tool handlers |
| internal/mcp/server.go | Minimal JSON-RPC 2.0 / MCP stdio server (stdlib only) | `Server`, `NewServer()`, `Register()`, `Serve()`, `ToolHandler` |
| internal/soccer/model.go | Core domain types and competition constants | `Match`, `Player`, `DB`, `CompetitionName()` |
| internal/soccer/loader.go | Parses the 6 heterogeneous CSVs into a unified DB; dedup + source selection | `Load()` |
| internal/soccer/query.go | Match/team/player query layer and standings | `FindMatches()`, `HeadToHead()`, `ComputeTeamStats()`, `FindPlayers()`, `Standings()` |
| internal/soccer/stats.go | Aggregate statistical analysis over the match corpus | `GoalStatistics()`, `BiggestWins()`, `BestRecords()`, `TopScoringTeams()`, `Competitions()`, `Seasons()` |
| internal/soccer/normalize.go | Team-name canonicalization / accent-folding for matching | `CanonicalName()`, `NameMatches()`, `MatchKey()`, `FoldAccents()`, `ParseCompetition()` |
| internal/soccer/format.go | Human-readable rendering of query results | `FormatMatchList()`, `FormatHeadToHead()`, `FormatTeamStats()`, `FormatStandings()`, ... |
| internal/soccer/soccer_test.go | Query/loader/stats unit tests | 17 test functions |
| internal/mcp/server_test.go | MCP protocol handshake / tools.list / tools.call tests | 5 test functions |
