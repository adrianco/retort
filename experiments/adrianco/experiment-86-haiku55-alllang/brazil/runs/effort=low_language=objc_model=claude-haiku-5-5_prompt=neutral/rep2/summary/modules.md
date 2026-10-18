# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.m | Loads datasets, serves MCP over stdin/stdout | `main()` |
| src/BSMCPServer.m | JSON-RPC 2.0 over NDJSON; tool registry | `BSMCPServer`, `-handleLine:`, `-registerToolNamed:...` |
| src/BSMCPTools.m | Registers the 9 soccer tools, formats answers | `BSMakeSoccerMCPServer()` |
| src/BSDataStore.m | Loads 6 CSVs, dedups matches, resolves teams | `BSDataStore`, `+storeWithDataDirectory:error:`, `-resolveTeam:` |
| src/BSCSVParser.m | RFC-style CSV reader (quotes, newlines, BOM, CRLF) | `BSReadCSVRows()` |
| src/BSQueryEngine.m | Match/team/player queries, standings, aggregates | `BSQueryEngine`, `-findMatches:`, `-standingsForSeason:...`, `-headToHeadBetweenKey:...`, `-searchPlayers:limit:`, `-teamProfileForKey:` |
| src/BSTextUtils.m | Team-name/competition/date normalization | `BSTeamKey()`, `BSCanonicalCompetition()`, `BSNormalizeDate()` |
| src/BSModels.m | Domain value objects | `BSMatch`, `BSPlayer`, `BSTeamRecord`, `BSHeadToHead` |
| tests/test_mcp.m | Protocol + tool scenarios | 14 scenarios |
| tests/test_queries.m | Query-logic scenarios | 16 scenarios |
| tests/test_parsing.m | CSV/date/name/competition parsing | 10 scenarios |
| tests/test_real_data.m | End-to-end over the real Kaggle data | 6 scenarios |
| tests/BSTestHarness.m | Minimal BDD scenario runner | `BSRegisterScenario()`, `BS_SCENARIO` |
