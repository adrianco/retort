# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/brazilian_soccer_mcp/core.clj | MCP server entry point — JSON-RPC 2.0 over stdin/stdout, dispatch to tools | `-main`, `handle-request` |
| src/brazilian_soccer_mcp/data.clj | Load + normalize the 6 Kaggle CSV datasets into in-memory maps | `load-all-data`, `normalize-date` |
| src/brazilian_soccer_mcp/tools.clj | Six query tools over the loaded data (matches, team stats, players, h2h, standings, stats) | `find-matches`, `get-team-stats`, `find-players`, `get-head-to-head`, `get-standings`, `get-statistics` |
| src/brazilian_soccer_mcp/normalize.clj | Team-name canonicalization across naming variants | `canonicalize`, `team-matches?` |
| test/brazilian_soccer_mcp/acceptance_test.clj | Executable acceptance suite (ATDD) over the tool API | 20 deftest vars |
| test/brazilian_soccer_mcp/core_test.clj | Unit tests for normalize / data helpers | 3 deftest vars |
