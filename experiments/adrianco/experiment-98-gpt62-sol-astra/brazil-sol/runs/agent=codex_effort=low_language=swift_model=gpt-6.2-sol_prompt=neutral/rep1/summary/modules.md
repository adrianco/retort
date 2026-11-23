# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/Soccer/CSV.swift | Hand-rolled RFC-4180 CSV reader (quotes, CRLF, BOM) | `CSV.read(_:)` |
| Sources/Soccer/Names.swift | Team/competition name + alias normalization to stable IDs | `Names.team(_:state:)`, `Names.competition(_:)`, `Names.key(_:)` |
| Sources/Soccer/Graph.swift | Dataset enum, `Match`/`Player` models, `SoccerGraph` loader that parses all CSVs, merges duplicate fixtures across sources, and builds team/player adjacency | `SoccerGraph(directory:)`, `Match`, `Player`, `Dataset` |
| Sources/Soccer/Queries.swift | `MatchFilter`, `Record`/`TeamRecords` aggregates, the `SoccerGraph.query(_:args:)` dispatcher, player search, pagination | `SoccerGraph.query(_:args:)`, `MatchFilter`, `Record` |
| Sources/Soccer/Analytics.swift | Competition standings/brackets/champions and match analytics (summary, team ranking, biggest wins) | `SoccerGraph.competitionSeason(...)`, `SoccerGraph.analyze(...)` |
| Sources/Soccer/MCP.swift | MCP JSON-RPC 2.0 server: tool schemas, arg validation, `initialize`/`ping`/`tools/list`/`tools/call` | `MCPServer`, `MCPServer.response(to:)` |
| Sources/SoccerServer/main.swift | stdio executable: builds the graph from `data/kaggle`, reads JSON-RPC lines, writes responses | `soccer-mcp` executable |
| Tests/SoccerTests/SoccerTests.swift | XCTest suite driving the server over real datasets | 7 test methods |
