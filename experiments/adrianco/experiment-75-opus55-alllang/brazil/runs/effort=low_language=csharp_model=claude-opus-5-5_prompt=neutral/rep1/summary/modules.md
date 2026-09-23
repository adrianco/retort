# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/SoccerMcp/Program.cs | Entrypoint: loads data, serves MCP over stdio or runs a one-shot CLI tool call | top-level statements |
| src/SoccerMcp/McpServer.cs | JSON-RPC 2.0 MCP server (initialize / tools/list / tools/call / ping) over newline-delimited stdio | `McpServer`, `RunAsync`, `Handle` |
| src/SoccerMcp/Tools.cs | 15 MCP tool definitions with JSON schemas and text-formatting handlers | `Tools`, `All`, `Call` |
| src/SoccerMcp/SoccerService.cs | Query layer over the data (matches, standings, team records, head-to-head, player search, stats) | `SoccerService`, `TeamRecord`, `HeadToHead` |
| src/SoccerMcp/DataStore.cs | Loads all six Kaggle CSVs into memory; data-dir discovery | `DataStore`, `Load`, `Default`, `FindDataDir` |
| src/SoccerMcp/Data.cs | Domain records + CSV parser + team-name normalization + date/int parsing + competition parsing | `Match`, `Player`, `Competitions`, `TeamNames`, `Csv`, `Parse` |
| tests/SoccerMcp.Tests/Fixture.cs | Shared xUnit data fixture (loads data once per run) | `DataFixture`, `DataCollection` |
| tests/SoccerMcp.Tests/QueryScenarios.cs | BDD-style scenario tests over the query/tool layer | 24 test methods |
| tests/SoccerMcp.Tests/McpProtocolTests.cs | JSON-RPC/MCP protocol tests | 6 test methods |
| tests/SoccerMcp.Tests/NormalizationTests.cs | Team-name / date / competition normalization tests | 5 test methods |
