# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| src/main.rs | Binary entrypoint: loads the graph from `data/kaggle` (or argv[1]) and serves MCP over stdio | `main()` |
| src/lib.rs | JSON-RPC 2.0 / MCP stdio server: handshake, `tools/list`, `tools/call`, errors | `serve()`, `Graph` (re-export) |
| src/data.rs | CSV ingestion, team-name normalization, date parsing, fixture de-duplication/merge across 6 sources | `Graph`, `Graph::load()`, `Match`, `Player`, `fold()`, `team_key()`, `competition()`, `date()`, `SOURCES` |
| src/query.rs | Query engine + tool schemas: match search, team stats, players, standings, cup brackets, analysis | `Graph::call()`, `tools()` |
| tests/behavior.rs | BDD-style integration tests over the loaded datasets + an end-to-end stdio MCP handshake test | 10 test functions |
