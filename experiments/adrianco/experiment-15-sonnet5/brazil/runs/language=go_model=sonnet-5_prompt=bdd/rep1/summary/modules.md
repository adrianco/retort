# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | Command entrypoint: loads data, builds registry, runs stdio server | `main()` |
| mcp.go | MCP JSON-RPC dispatch, tool registry, initialize/tools/list/tools/call | `Server`, `ToolRegistry`, `Tool`, `NewServer()` |
| jsonrpc.go | JSON-RPC 2.0 request/response envelope helpers | `rpcRequest`, `rpcResponse`, `newResult()`, `newError()` |
| tools.go | Registers the 10 MCP tools and their handlers/arg structs | `BuildToolRegistry()`, `handle*` |
| store.go | In-memory data store + all query/aggregation logic | `Store`, `FilterMatches()`, `HeadToHead()`, `TeamRecord()`, `Standings()`, `SearchPlayers()`, `BiggestWins()`, `StatsSummary()`, `BestRecord()`, `TeamPlayers()` |
| loader.go | Reads the 6 Kaggle CSVs, normalizes to `Match`/`Player`, dedupes | `LoadAll()` |
| dateparse.go | Flexible multi-format date parsing (ISO, Brazilian DD/MM/YYYY, with time) | `ParseFlexibleDate()` |
| normalize.go | Team/club name normalization (accents, state suffixes, alias table) | `NormalizeTeamName()` |
| models.go | Core data types | `Match`, `Player` |
| dateparse_test.go | Date parsing tests | 5 test functions |
| loader_test.go | Dataset loading / dedup tests (real data) | 4 test functions |
| mcp_test.go | JSON-RPC protocol + registry tests | 6 test functions |
| normalize_test.go | Name normalization tests | 6 test functions |
| store_test.go | Query/aggregation logic tests | 13 test functions |
| tools_test.go | Tool handler integration tests (real data) | 8 test functions |

Non-source excluded: `data/` (input CSVs), `brazilian-soccer-mcp` (compiled binary), `*.md`, `prompts.txt`, `_*.log`/`_*.json`.
