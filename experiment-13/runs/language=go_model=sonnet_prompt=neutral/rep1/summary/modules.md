# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | MCP JSON-RPC server over stdio; protocol types, tool registry, request dispatch | `main()`, `NewServer()`, `Server.Run()`, `Server.handleRequest()`, `Server.buildTools()`, `Server.callTool()` |
| tools.go | Tool implementations that format query results as text | `Server.toolSearchMatches`, `toolTeamStats`, `toolStandings`, `toolBiggestWins`, `toolSearchPlayers`, `toolCompetitionStats`, `toolListTeams` |
| data.go | CSV loaders, unified `Match`/`Player` models, name/date normalization, query + aggregation helpers | `LoadDatabase()`, `Database.FilterMatches`, `FilterMatchesH2H`, `TeamStats`, `Standings`, `BiggestWins`, `FilterPlayers`, `GoalsPerMatch`, `HomeWinRate`, `TopScoringTeams`, `Seasons` |
| mcp_test.go | Unit + integration + MCP-protocol tests against the real CSVs | 25 `Test*` functions incl. `TestSample20Questions` (20 subtests) |

(Build artifact `brazilian-soccer-mcp` and `data/kaggle/*.csv` excluded.)
