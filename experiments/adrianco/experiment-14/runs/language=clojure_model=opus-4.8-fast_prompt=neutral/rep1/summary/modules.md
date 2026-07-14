# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/brsoccer/main.clj | Entry point; eagerly loads the graph then serves MCP over stdio | `-main` |
| src/brsoccer/mcp.clj | MCP/JSON-RPC 2.0 server: tool definitions, dispatch, stdio transport | `tools`, `call-tool`, `handle-request`, `serve!`, `tool-list-payload` |
| src/brsoccer/data.clj | Loads the six Kaggle CSVs into an in-memory knowledge graph (matches/players/teams/by-team), with dedup | `load-graph`, `graph`, `reset-cache!` |
| src/brsoccer/query.clj | Pure query/analytics layer over the graph (matches, records, h2h, players, standings, stats) | `find-matches`, `team-record`, `head-to-head`, `search-players`, `players-by-brazilian-club`, `standings`, `biggest-wins`, `summary-stats`, `best-record`, `list-competitions`, `resolve-team` |
| src/brsoccer/normalize.clj | All string/value normalization: team-key canonicalization, accent/suffix stripping, date and number parsing | `team-key`, `strip-accents`, `strip-suffix`, `clean-name`, `parse-date`, `parse-int`, `parse-num`, `year-of` |
| src/brsoccer/format.clj | Renders query results into the spec's human-readable text blocks | `match-line`, `matches-block`, `record-block`, `head-to-head-block`, `players-block`, `standings-block`, `stats-block`, `competitions-block` |
| test/brsoccer/query_test.clj | Query logic tests (synthetic graph + real-dataset coverage) | 11 deftests |
| test/brsoccer/mcp_test.clj | MCP protocol layer tests (handshake, tools/list, tools/call, stdio round-trip) | 9 deftests |
| test/brsoccer/normalize_test.clj | Normalization tests (keys, suffixes, dates, aliases) | 6 deftests |
