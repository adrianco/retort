# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| Sources/soccer-mcp/main.swift | Executable entrypoint: locates `data/kaggle`, loads DB, runs the stdio read-line loop | `main` (top-level) |
| Sources/SoccerCore/MCPServer.swift | JSON-RPC 2.0 over stdio; dispatches initialize/ping/tools.list/tools.call | `MCPServer`, `handle(line:)` |
| Sources/SoccerCore/ToolCatalog.swift | Tool descriptors (name, description, JSON Schema) for tools/list | `ToolCatalog.definitions` |
| Sources/SoccerCore/Tools.swift | Tool implementations: parses args, calls query engine, formats text | `ToolHandler`, `call(_:arguments:)`, `ToolError` |
| Sources/SoccerCore/Analytics.swift | Query engine: match search, team record, h2h, standings, ranking, league stats, player search | `MatchFilter`, `Tally`, `LeagueStats`, `RankMetric`, `SoccerDatabase` extension |
| Sources/SoccerCore/QueryRouter.swift | Maps natural-language questions to a tool + arguments for the `ask` tool | `QueryRouter.route(_:db:)` |
| Sources/SoccerCore/Database.swift | In-memory container of matches + players | `SoccerDatabase` |
| Sources/SoccerCore/Models.swift | Value types: `Match`, `Player`, `TeamKey`, `CalendarDate`, `Competition` | `Match`, `Player`, `TeamKey`, `CalendarDate` |
| Sources/SoccerCore/DataLoader.swift | Reads the six Kaggle CSVs, maps columns, dedupes overlapping seasons | `DataLoader.load(directory:)` |
| Sources/SoccerCore/CSV.swift | Quote-aware CSV parser | `CSVTable`, `CSVTable.load(url:)` |
| Sources/SoccerCore/TextNormalization.swift | Accent/case folding, team-name normalization | `TeamNormalizer`, `foldWords` |
| Sources/SoccerCore/Positions.swift | Player-position word → FIFA position-code mapping | `Positions.codes(for:)` |
| Sources/SoccerCore/Formatting.swift | Human-readable match/record/standing/player line formatting | `Formatting` |
| Tests/SoccerCoreTests/AnalyticsTests.swift | Query-engine unit tests over a fixture DB | 14 test functions |
| Tests/SoccerCoreTests/MCPServerTests.swift | JSON-RPC protocol + tool-call tests | 10 test functions |
| Tests/SoccerCoreTests/QueryRouterTests.swift | NL routing tests | 11 test functions |
| Tests/SoccerCoreTests/NormalizationTests.swift | Team-name/accent folding tests | 11 test functions |
| Tests/SoccerCoreTests/DataLoaderTests.swift | Acceptance tests against the real Kaggle CSVs | 6 test functions |
| Tests/SoccerCoreTests/CSVTests.swift | CSV parser tests | 5 test functions |
| Tests/SoccerCoreTests/TestSupport.swift | Fixture DB + match/player builders | `Fixture` |
