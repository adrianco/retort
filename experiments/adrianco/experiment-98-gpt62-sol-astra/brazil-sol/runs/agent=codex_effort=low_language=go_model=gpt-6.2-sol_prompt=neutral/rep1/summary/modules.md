# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | JSON-RPC 2.0 MCP server over stdio; dispatch of initialize/ping/tools/list/tools/call | `serve()`, `dispatch()`, `main()` |
| tools.go | Tool definitions and schemas; the six MCP tools and their arg structs | `soccerTools()`, `defineTool()`, `analyzeMatches()`, `Tool` |
| query.go | Match/player filtering, aggregation (records, standings, summaries, player search) | `findMatches()`, `findPlayers()`, `teamStats()`, `standings()`, `summarize()`, `teamRecords()`, `clubRatings()` |
| data.go | CSV loading, parsing, name/competition/date normalization | `loadStore()`, `loadMatch()`, `readCSV()`, `clubName()`, `competitionName()`, `parseDate()`, `words()` |
| fixtures.go | Cross-source match reconciliation, derby/rivalry detection, stage naming | `reconcileMatches()`, `derby()`, `stageName()`, `matchesStage()` |
| soccer_test.go | Table-driven tests: dataset load counts, 27 sample-question cases, MCP stdio round-trip, reconciliation | `TestAllProvidedFilesAreQueryable`, `TestSoccerQuestions`, `TestReconciledFixtureCarriesAvailableSourceFields`, `TestMCPStdio` |

No external dependencies (no `go.sum`; standard library only).
