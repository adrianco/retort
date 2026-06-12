# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Process entry point: resolve data dir, load datasets, register tools, run stdio loop | `main()`, `defaultDataDir()` |
| mcp.go | Dependency-free MCP/JSON-RPC 2.0 server over stdio (initialize, tools/list, tools/call) | `Server`, `NewServer()`, `Tool`, `(*Server).AddTool`, `(*Server).Serve` |
| tools.go | Defines the 7 MCP tools and the handlers turning JSON args into Store queries + text answers | `RegisterTools()`, handlers, `objectSchema()` |
| store.go | In-memory query engine: match lookup, team stats, head-to-head, standings, competition stats, player search | `Store`, `FindMatches`, `TeamStats`, `HeadToHead`, `Standings`, `Stats`, `SearchPlayers` |
| loader.go | Reads the six bundled Kaggle CSVs (header-mapped, BOM-tolerant) into normalized types | `LoadAll()`, `loadMatchFile()`, `loadPlayers()` |
| model.go | Core domain types shared across loader/store/tools | `Match`, `Player`, `(Match).Winner`, `(Match).signature` |
| normalize.go | Team-name / date / number canonicalization (accent folding, state suffixes) | `normKey`, `teamKey`, `teamFullKey`, `baseAndState`, `parseDate`, `atoi` |
| loader_test.go | Integration tests against the real bundled datasets | 4 test functions |
| store_test.go | Query-engine unit tests | 9 test functions |
| normalize_test.go | Normalization unit tests | 6 test functions |
| mcp_test.go | JSON-RPC protocol / tool-dispatch tests | 6 test functions |
