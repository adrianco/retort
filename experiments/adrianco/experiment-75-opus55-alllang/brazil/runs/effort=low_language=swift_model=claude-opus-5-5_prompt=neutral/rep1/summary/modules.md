# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/BrazilianSoccerMCP/main.swift | Executable entrypoint: loads data, wires QueryEngine → SoccerTools → MCPServer, runs stdio loop | top-level `do`/`server.run()` |
| Sources/SoccerKit/MCPServer.swift | JSON-RPC 2.0 MCP server over stdio (initialize, ping, tools/list, tools/call) | `MCPServer`, `handle(line:)`, `run()` |
| Sources/SoccerKit/Tools.swift | 13 MCP tool definitions + text-formatted handlers dispatching to QueryEngine | `SoccerTools`, `definitions`, `call(_:_:)` |
| Sources/SoccerKit/QueryEngine.swift | Core query/aggregation logic: matches, records, standings, stats, players | `QueryEngine`, `findMatches`, `headToHead`, `teamRecord`, `standings`, `summary`, `searchPlayers` |
| Sources/SoccerKit/DataStore.swift | Loads and de-duplicates 6 Kaggle CSVs into `[Match]` + `[Player]` | `DataStore`, `init(directory:)`, `defaultDirectory()` |
| Sources/SoccerKit/Models.swift | Domain types: `Competition`, `Match`, `Player`, display helper | `Competition`, `Match`, `Player`, `display(_:)` |
| Sources/SoccerKit/Normalize.swift | Team-name folding/aliasing/keying and date parsing | `TeamName.key`, `TeamName.matches`, `DateParse.parse`, `DateParse.format` |
| Sources/SoccerKit/CSV.swift | RFC4180-style CSV parser (quotes, embedded commas/newlines, BOM) | `CSV.parse`, `CSV.records` |
| Tests/SoccerKitTests/UnitTests.swift | Unit tests for CSV, normalization, dates, competition parsing, synthetic standings | 5 test functions |
| Tests/SoccerKitTests/FeatureTests.swift | BDD-style feature tests over the real datasets + MCP protocol | 29 test functions |
