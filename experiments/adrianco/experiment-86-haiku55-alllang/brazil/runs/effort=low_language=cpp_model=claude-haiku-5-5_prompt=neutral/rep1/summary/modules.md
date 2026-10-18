# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.cpp | Entry point: load datasets, serve MCP over stdin/stdout | `main()` |
| src/mcp_server.hpp / .cpp | JSON-RPC 2.0 MCP server; 6 tools dispatched to the query layer | `McpServer`, `handleMessage()`, `run()`, `listTools()`, `callTool()` |
| src/queries.hpp / .cpp | Structured queries over the dataset (matches, records, standings, players, stats) | `findMatches()`, `teamRecord()`, `headToHead()`, `standings()`, `searchPlayers()`, `goalStats()` |
| src/dataset.hpp / .cpp | Loads the 6 Kaggle CSVs into `Match`/`Player`, dedups fixtures | `Dataset`, `Dataset::load()`, `Match`, `Player` |
| src/csv.hpp / .cpp | CSV parser (header-indexed rows) | `parseCsv()`, `readCsvFile()`, `CsvTable` |
| src/text.hpp / .cpp | Team-name/competition normalization, date & int parsing, accent folding | `canonicalTeamKey()`, `stripTeamDecorations()`, `parseDate()`, `parseInt()`, `foldText()`, `trim()` |
| src/json.hpp / .cpp | Hand-rolled JSON value, parser and serializer | `Json`, `Json::parse()`, `Json::dump()` |
| tests/test_framework.hpp | Minimal `TEST_CASE`/`CHECK` harness + shared dataset fixture | `TEST_CASE`, `CHECK`, `CHECK_EQ`, `sharedDataset()` |
| tests/test_main.cpp | Test runner: executes every registered case | `main()`, `registry()` |
| tests/query_tests.cpp | Scenario tests of the query layer against real data | 14 `TEST_CASE`s |
| tests/mcp_tests.cpp | JSON-RPC protocol + tool-dispatch tests | 10+ `TEST_CASE`s |
| tests/json_csv_tests.cpp | JSON and CSV parser unit tests | ~8 `TEST_CASE`s |
| tests/text_tests.cpp | Text-normalization unit tests | ~9 `TEST_CASE`s |
