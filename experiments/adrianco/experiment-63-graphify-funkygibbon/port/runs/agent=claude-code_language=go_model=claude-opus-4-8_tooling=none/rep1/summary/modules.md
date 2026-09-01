# Modules

Port lives in a new top-level `wombat-go/` directory (additive; Python/TypeScript clients untouched). Standard-library-only Go module.

| Path | Purpose | Entry points |
|------|---------|--------------|
| wombat-go/cmd/wombat-mcp/main.go | Process entrypoint: opens cache, optional seed, initial + background sync, serves stdio MCP | `main`, `run` |
| wombat-go/internal/version/version.go | Canonical inbetweenies-v2 version-string format/parse/compare | `FormatTime`, `New`, `Timestamp`, `Compare`, `Greater`, `NextCounter` |
| wombat-go/internal/protocol/protocol.go | inbetweenies-v2 wire types (SyncRequest/Response, changes, filters, stats, conflicts) | `SyncRequest`, `SyncResponse`, `EntityChange`, `RelationshipChange`, `SyncChange`, `SyncFilters` |
| wombat-go/internal/conflict/conflict.go | Canonical LWW + 1s-window version-tiebreak resolver | `Resolve`, `Side`, `Resolution` |
| wombat-go/internal/graph/graph.go | Durable JSON-file graph cache (latest-version-per-id, tombstones, watermark) | `Open`, `Store`, `PutEntity`, `PutRelationship`, `Get*`, `RelationshipsTo/From`, `SetWatermark` |
| wombat-go/internal/syncengine/engine.go | Sync client: request build, bearer auth POST, apply ordering, conflict resolution, watermark advance | `New`, `Engine`, `BuildRequest`, `Sync`, `ApplyResponse` |
| wombat-go/internal/tools/tools.go | The 12 knowledge-graph MCP tools backed by the cache | `New`, `Tools`, `Execute`, per-tool methods |
| wombat-go/internal/tools/args.go | Argument coercion helpers for tool dispatch | `str`, `strList`, `intArg`, `floatArg`, `objArg` |
| wombat-go/internal/mcp/server.go | JSON-RPC 2.0 stdio server (initialize/tools.list/tools.call) | `NewServer`, `Server`, `Handle`, `Serve`, `ReducePayload` |
| wombat-go/internal/mcp/tools_schema.go | Exact 12-tool schema surface for tools/list | `ToolDefs`, `ToolDef` |
| wombat-go/internal/seed/seed.go | Load a knowledge-graph.json snapshot into the cache (offline seed) | `LoadFile` |
| wombat-go/internal/fixtures/fixtures.go | Test-only fixtures locator (`../../fixtures`) | `Read` |
| wombat-go/internal/version/version_test.go | Version-string conformance vs fixtures/version-strings.json | 6 test functions |
| wombat-go/internal/conflict/conflict_test.go | Conflict-resolution conformance vs sync-exchanges tiebreak | test functions |
| wombat-go/internal/graph/graph_test.go | Cache persistence/tombstone tests | test functions |
| wombat-go/internal/syncengine/engine_test.go | Sync request/apply/watermark conformance vs sync-exchanges.json | test functions |
| wombat-go/internal/tools/tools_test.go | 12-tool golden conformance vs mcp-tool-golden.json | test functions |
| wombat-go/internal/mcp/server_test.go | JSON-RPC/stdio server tests (tools/list count, tools/call) | test functions |

30 test functions total across 6 `_test.go` files; ~1,894 non-test LOC, ~776 test LOC.
