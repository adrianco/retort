# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/brazilian_soccer_mcp/csv.clj | Self-contained RFC-4180-ish CSV reader → vector of row maps | `parse-line`, `read-csv` |
| src/brazilian_soccer_mcp/core.clj | Data loading, team-name normalization, and all query/aggregation logic | `load-data`, `search-matches`, `team-stats`, `head-to-head`, `search-players`, `standings`, `dataset-statistics`, `team-key`, `fold` |
| src/brazilian_soccer_mcp/server.clj | stdio JSON-RPC MCP server: tool definitions + dispatch | `-main`, `handle`, `dispatch`, `tool-definitions` |
| test/brazilian_soccer_mcp/core_test.clj | clojure.test suite over query fns + MCP protocol + real corpus | 5 `deftest` blocks, 15 assertions |
| test/brazilian_soccer_mcp/test_runner.clj | Runs tests and exits non-zero on failure | `-main` |
