# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entrypoint: parse `-data` flag, load store, serve MCP over stdio | `main()` |
| server.go | MCP JSON-RPC stdio transport, tool schema registry, tool dispatch | `Serve()`, `toolList()`, `strictJSON()` |
| data.go | CSV ingestion of all six datasets, team-name normalization, dedup/merge | `Load()`, `team()`, `competition()`, `date()`, `number()`; types `Match`, `Player`, `Store` |
| query.go | Query filtering, aggregation (records/standings/stats), pagination | `(*Store).Call()`, `matches()`, `players()`, `records()`, `summary()`; type `Query` |
| soccer_test.go | Unit + integration tests over fixtures and the real datasets | 7 test functions (`TestGivenMatchesWhenSearching…`, `TestMCPTransport`, `TestAllDatasetsAndTwentySampleQuestions`, …) |
