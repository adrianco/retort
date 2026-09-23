# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/soccer/data.clj | CSV loading + team-name/date normalization; builds the in-memory db | `load-all`, `db`, `team-key`, `display-name`, `parse-date`, `read-csv` |
| src/soccer/query.clj | Query & statistics functions over the loaded db | `find-matches`, `team-stats`, `head-to-head`, `standings`, `summary-stats`, `best-records`, `find-players`, `players-by-club-summary`, `cup-finals`, `derbies` |
| src/soccer/server.clj | MCP (JSON-RPC 2.0 over stdio) server; 13 tool definitions + handlers | `-main`, `handle`, `call-tool`, `tools`, `tool-descriptor` |
| test/soccer/core_test.clj | BDD-style Given/When/Then test suite | 25 `deftest` scenarios |

Non-source, pre-seeded: `deps.edn`, `README.md`, `brazilian-soccer-mcp-guide.md` (spec), `data/kaggle/*.csv` (6 datasets).
