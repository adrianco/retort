# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | JSON-RPC (MCP) server over stdio; tool registry + dispatch | `main()`, `server.serve`, `server.handle`, `server.tools`, `server.callTool` |
| soccer/loader.go | CSV ingestion of match/player datasets; team-name normalization | `LoadAll`, `NormalizeTeam`, `TeamMatches`, `Match`, `Player`, `DB` |
| soccer/query.go | Query/aggregation layer over loaded data | `MatchesByTeam`, `MatchesBetween`, `H2H`, `TeamStats`, `Standings`, `BiggestWins`, `AverageGoalsPerMatch`, `PlayersByName`, `PlayersByClub`, `PlayersByNationality`, `TopPlayers`, `FormatMatches` |
| soccer/soccer_test.go | Unit tests for loader + query layer | 13 `Test*` functions |
