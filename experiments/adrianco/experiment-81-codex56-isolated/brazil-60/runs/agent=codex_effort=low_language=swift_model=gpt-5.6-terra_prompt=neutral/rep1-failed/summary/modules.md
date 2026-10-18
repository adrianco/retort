# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/BrazilianSoccerMCP/main.swift | MCP stdio JSON-RPC loop; tool registry + dispatch | `toolDefinitions`, `handle(name:args:store:)`, top-level read loop |
| Sources/BrazilianSoccerMCP/SoccerStore.swift | Loads CSVs, normalizes names, runs match/team/player/standings queries | `SoccerStore`, `findMatches`, `teamRecord`, `headToHead`, `searchPlayers`, `standings`, `normalized` |
| Sources/BrazilianSoccerMCP/Models.swift | Value types for match, player, and aggregated record | `Match`, `Player`, `Record` |
| Sources/BrazilianSoccerMCP/CSV.swift | RFC-4180-style CSV reader (quotes, embedded newlines) | `CSV.rows(at:)`, `CSV.parse(_:)` |
| Tests/BrazilianSoccerMCPTests/SoccerStoreTests.swift | Unit tests for CSV parse, name normalization, store search/record | 3 test functions |
