# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/brazilian_soccer_mcp/core.clj | MCP JSON-RPC server over stdio: dispatches `initialize`, `tools/list`, `tools/call` | `-main`, `run-server`, `handle-message` |
| src/brazilian_soccer_mcp/data.clj | CSV loading + per-dataset row normalization into in-memory atom | `load-all-data!`, `get-fifa`, `get-all-matches`, `matches-for-competition`, `parse-csv-file` |
| src/brazilian_soccer_mcp/normalize.clj | Team-name normalization, fuzzy matching, date/number parsing, output formatting | `normalize-team`, `team-matches?`, `parse-date`, `parse-int`, `match-result-line`, `competition-label` |
| src/brazilian_soccer_mcp/tools.clj | The 7 query tools + JSON tool-schema registry + dispatch | `call-tool`, `tool-definitions`, `search-matches`, `get-team-stats`, `search-players`, `get-standings`, `get-head-to-head`, `get-biggest-wins`, `get-competition-stats` |
| test/brazilian_soccer_mcp/tools_test.clj | clojure.test suite over normalize, data loading, and all 7 tools | 14 deftest functions |
