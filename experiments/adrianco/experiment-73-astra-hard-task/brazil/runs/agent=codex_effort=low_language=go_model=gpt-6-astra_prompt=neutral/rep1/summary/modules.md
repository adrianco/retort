# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | MCP JSON-RPC stdio server: tool catalog, request routing, `initialize`/`tools/list`/`tools/call` lifecycle | `main()`, `Server.handle()`, `Server.Serve()`, `specs()` |
| data.go | CSV loading, team/date/score normalization, cross-source match dedup + enrichment | `Load()`, `Store.loadFile()`, `team()`, `competition()`, `parseDate()`, `score()` |
| query.go | Query engine over the in-memory store: filtering, aggregation, standings, head-to-head, graph, pagination | `Store.Query()`, `Store.matches()`, `record()`, `table()`, `summary()`, `Filter.validate()` |
| soccer_test.go | Unit + integration tests over the real datasets and synthetic fixtures | 17 test functions, 2 benchmarks |
