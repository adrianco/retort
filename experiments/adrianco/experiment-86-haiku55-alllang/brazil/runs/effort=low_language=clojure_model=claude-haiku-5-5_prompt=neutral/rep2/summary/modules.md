# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/brazilian_soccer/server.clj | MCP server over stdio (newline-delimited JSON-RPC 2.0); dispatch of initialize/ping/tools.list/tools.call | `serve`, `handle-message`, `handle-line`, `-main` |
| src/brazilian_soccer/tools.clj | MCP tool definitions + plain-text formatting of query results | `tool-specs`, `tool-descriptors`, `call-tool` |
| src/brazilian_soccer/queries.clj | Pure query functions over loaded match/player records | `search-matches`, `team-record`, `head-to-head`, `standings`, `league-stats`, `search-players`, `brazilian-club-summary`, `resolve-team` |
| src/brazilian_soccer/data.clj | Loads the 6 Kaggle CSVs into normalized match/player records; dedup | `load-all`, `load-matches-from`, `load-players-from`, `parse-date`, `parse-whole` |
| src/brazilian_soccer/names.clj | Team/competition name normalization across datasets (accents, suffixes, aliases) | `team-key`, `competition-key`, `normalize-text`, `base-name` |
| src/brazilian_soccer/csv.clj | Minimal RFC 4180 CSV reader (quotes, BOM, CRLF) | `parse-rows`, `read-maps` |
| src/brazilian_soccer/json.clj | Small JSON encoder/decoder for JSON-RPC messages | `encode`, `decode` |
| test/brazilian_soccer/test_runner.clj | Runs every test ns, exits non-zero on failure | `-main` |
| test/brazilian_soccer/fixtures.clj | Shared in-memory match/player fixtures | `matches`, `players` |
| test/brazilian_soccer/server_test.clj | MCP protocol + tool dispatch tests | 10 deftests |
| test/brazilian_soccer/queries_test.clj | Query-function tests | 13 deftests |
| test/brazilian_soccer/data_test.clj | Parsing + smoke tests against the real Kaggle files | 9 deftests |
| test/brazilian_soccer/json_test.clj | JSON round-trip tests | 7 deftests |
| test/brazilian_soccer/names_test.clj | Name-normalization tests | 6 deftests |
| test/brazilian_soccer/csv_test.clj | CSV-parser tests | 4 deftests |
