# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/BrazilianSoccerMcp/Program.cs | Top-level entry: loads data dir, builds database, runs the MCP server over stdio | top-level statements |
| src/BrazilianSoccerMcp/Mcp/McpServer.cs | JSON-RPC 2.0 MCP server over newline-delimited stdio (initialize, ping, tools/list, tools/call) | `McpServer`, `RunAsync()`, `HandleMessage()` |
| src/BrazilianSoccerMcp/Mcp/SoccerTools.cs | Defines the six soccer tools and formats their plain-text answers | `SoccerTools`, `All` |
| src/BrazilianSoccerMcp/Mcp/McpTool.cs | Tool record plus `ToolArguments` and `Schema` helpers | `McpTool`, `ToolArguments`, `Schema` |
| src/BrazilianSoccerMcp/Data/DatasetLoader.cs | Reads the six Kaggle CSVs into domain Matches and Players | `DatasetLoader`, `Load()`, `Dataset` |
| src/BrazilianSoccerMcp/Data/SoccerDatabase.cs | In-memory index + all read-only queries (matches, stats, h2h, standings, league summary, players) | `SoccerDatabase`, `FindMatches()`, `GetTeamStats()`, `GetHeadToHead()`, `GetStandings()`, `GetLeagueSummary()`, `SearchPlayers()`, `ResolveTeam()` |
| src/BrazilianSoccerMcp/Data/FieldParser.cs | Parses the dataset's multiple date and number formats | `FieldParser`, `Date()`, `Int()` |
| src/BrazilianSoccerMcp/Data/TeamNames.cs | Normalises club names/aliases to canonical match keys | `TeamNames`, `Parse()` |
| src/BrazilianSoccerMcp/Data/TextNormalizer.cs | Folds text (lowercase, accent-strip, punctuation to spaces) for comparison | `TextNormalizer`, `Fold()` |
| src/BrazilianSoccerMcp/Csv/CsvReader.cs | RFC 4180 CSV reader with BOM handling; rows addressed by column name | `CsvReader`, `Read()`, `CsvRecord` |
| src/BrazilianSoccerMcp/Domain/Models.cs | Domain records: Match, Player, queries, results, stats | `Match`, `Player`, `Venue`, `MatchQuery`, `PlayerQuery`, `SearchResult<T>`, `TeamStats`, `HeadToHead`, `LeagueSummary`, `TeamRef` |
| tests/BrazilianSoccerMcp.Tests/CsvReaderTests.cs | CSV parsing tests | 4 test methods |
| tests/BrazilianSoccerMcp.Tests/DatasetLoaderTests.cs | Dataset loading tests | 4 test methods |
| tests/BrazilianSoccerMcp.Tests/McpServerTests.cs | JSON-RPC protocol tests | 8 test methods |
| tests/BrazilianSoccerMcp.Tests/SampleQuestionTests.cs | End-to-end sample-question coverage | 1 (Theory) |
| tests/BrazilianSoccerMcp.Tests/SoccerDatabaseTests.cs | Query/aggregation logic tests | 15 test methods |
| tests/BrazilianSoccerMcp.Tests/TeamNameTests.cs | Team-name normalisation tests | 4 test methods |
| tests/BrazilianSoccerMcp.Tests/TestData.cs | Shared in-memory test fixtures | helpers (no tests) |

Build artifacts under `bin/` and `obj/` were not read.
