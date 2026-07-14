# Modules

| Path | Purpose | Entry points |
|------|---------|--------------|
| main.go | CLI entry: parse `-data` flag, load datasets, start MCP stdio server | `main()` |
| internal/mcp/protocol.go | JSON-RPC 2.0 / MCP wire types and error codes | `Request`, `Response`, `RPCError`, `Tool`, `ToolResult`, `ToolContent`, `ProtocolVersion` |
| internal/mcp/server.go | Server read-eval-respond loop, request dispatch, tool-call routing | `Server`, `NewServer()`, `(*Server).Serve()`, `(*Server).Tools()` |
| internal/mcp/tools.go | Tool registration, JSON-schema builders, arg coercion, handlers, output formatting | `(*Server).registerTools()`, handlers (`handleSearchMatches`, etc.) |
| internal/soccer/models.go | Domain types for matches and players | `Match`, `Player`, `Result`, `(Match).Decided/TotalGoals/ResultFor` |
| internal/soccer/store.go | In-memory store, fixture dedup, canonical display names | `Store`, `NewStore()`, `Index()`, `DisplayName()`, `Teams()`, `Seasons()`, `Competitions()` |
| internal/soccer/loader.go | Per-file CSV parsers for the six datasets; `LoadDir` orchestration | `LoadDir()`, file-name constants, `parseDate/parseGoals` |
| internal/soccer/queries.go | Typed query engine (matches, head-to-head, team record, standings, players, stats) | `FindMatches()`, `HeadToHead()`, `TeamRecord()`, `Standings()`, `FindPlayers()`, `Stats()` |
| internal/soccer/normalize.go | Team/name normalisation, accent folding, club alias table | `NormalizeTeam()`, `NormalizeName()`, `CleanTeam()` |
| internal/mcp/server_test.go | MCP server/protocol tests | 9 test functions |
| internal/soccer/integration_test.go | End-to-end store/query integration tests | 4 test functions |
| internal/soccer/loader_test.go | CSV loader tests | 5 test functions |
| internal/soccer/normalize_test.go | Normalisation/alias tests | 9 test functions |
| internal/soccer/queries_test.go | Query-engine tests | 12 test functions |
| internal/soccer/store_test.go | Store/dedup/display-name tests | 5 test functions |
