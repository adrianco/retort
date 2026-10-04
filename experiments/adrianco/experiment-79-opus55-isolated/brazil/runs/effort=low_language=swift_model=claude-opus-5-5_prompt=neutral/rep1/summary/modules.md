# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Package.swift | SwiftPM manifest: library `BrazilianSoccer` + executable `brazilian-soccer-mcp`, macOS 13, one test target | `package` |
| Sources/BrazilianSoccer/Models.swift | Core value types: dates, competitions, matches, players, records | `SimpleDate`, `Competition`, `Match`, `MatchStats`, `Player`, `Venue`, `Record` |
| Sources/BrazilianSoccer/CSV.swift | RFC 4180 CSV byte-level parser (quotes, CRLF, BOM) + header/table reader | `CSV.parse(_:)`, `CSV.table(at:)` |
| Sources/BrazilianSoccer/TeamNames.swift | Team-name folding, alias/affix stripping, state disambiguation, canonical-key resolution | `TeamNames.fold(_:)`, `TeamNames.parse(_:state:)`, `TeamResolver` |
| Sources/BrazilianSoccer/DataStore.swift | Loads the six CSVs into memory, de-duplicates matches, builds players, locates the data dir | `DataStore(directory:)`, `DataStore.locateDataDirectory(...)`, `teamName(_:)` |
| Sources/BrazilianSoccer/Queries.swift | Query layer over `DataStore`: match filtering, records, standings, rankings, derbies, player search | `MatchFilter`, `findMatches`, `record(for:)`, `standings`, `ranking`, `findPlayers`, `PlayerFilter` |
| Sources/BrazilianSoccer/Tools.swift | 15 MCP tools: parse args, run a query, format text answers; the tool catalogue + JSON schemas | `SoccerTools`, `Tool`, `SoccerTools.tools`, `SoccerTools.call(_:arguments:)` |
| Sources/BrazilianSoccer/MCPServer.swift | JSON-RPC 2.0 dispatcher over stdio (initialize, tools/list, tools/call, ping, …) | `MCPServer`, `handle(line:)` |
| Sources/brazilian-soccer-mcp/main.swift | Executable entry: locate data, build store, read stdin lines, write JSON-RPC to stdout | top-level program |
| Tests/BrazilianSoccerTests/DataStoreTests.swift | Loading, de-dup, records, standings, rankings, derbies, player joins, performance | 17 test functions |
| Tests/BrazilianSoccerTests/ParsingTests.swift | CSV, date formats, team-name parsing/resolution, competition names | 7 test functions |
| Tests/BrazilianSoccerTests/ToolAndServerTests.swift | Sample questions, formatting, arg validation, MCP handshake, schemas, protocol errors | 7 test functions |
| Tests/BrazilianSoccerTests/Support.swift | Shared test helper (locates data dir / builds a store) | helpers, no test functions |
