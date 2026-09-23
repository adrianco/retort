# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.m | Entry point: MCP stdio server, or one-shot CLI tool call | `main()` |
| src/BSCSV.{h,m} | RFC 4180 CSV parser (quotes, embedded commas, BOM, UTF-8) | `BSCSV +parseString:`, `+recordsFromFile:error:` |
| src/BSTeamNames.{h,m} | Team-name normalization across dataset naming variants | `BSTeamNames +keyForName:state:` |
| src/BSModels.{h,m} | Match and player value objects | `BSMatch`, `BSPlayer`, `-summary` |
| src/BSDatabase.{h,m} | In-memory knowledge base over the 6 CSVs; loads, de-duplicates, and runs all queries | `BSDatabase -initWithDataDirectory:error:`, `BSTeamRecord`, query methods |
| src/BSTools.{h,m} | 15 MCP tool schemas + formatted text answers | `BSTools -toolDefinitions`, `-callTool:arguments:isError:` |
| src/BSMCPServer.{h,m} | JSON-RPC 2.0 dispatch over stdio | `BSMCPServer -handleMessage:`, `-handleLine:`, `-runStdio` |
| tests/BSTests.m | BDD (Given/When/Then) suite, 32 scenarios | `main()` |
