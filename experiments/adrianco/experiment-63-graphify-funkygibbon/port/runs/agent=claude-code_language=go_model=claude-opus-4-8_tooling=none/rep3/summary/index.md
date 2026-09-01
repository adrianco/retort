# Architecture summary — wombat-go

A new additive top-level directory `wombat-go/` (Go module
`github.com/adrianco/the-goodies/wombat-go`, Go 1.22, **no external deps** — pure
stdlib) porting the FunkyGibbon MCP client per the inbetweenies-v2 spec. The
Python (`blowing-off`) and TypeScript (`kittenkong`) clients are untouched.

## Packages

| Package | Files | Role |
|---------|-------|------|
| `version/` | version.go | Canonical version strings: `Format`/`FormatUTC` emit `{utc-iso8601}-{counter:06d}-{user_id}` (`+00:00`, no `Z`); `Timestamp` parses (tolerates legacy `Z`, hyphenated user_id via `[+-]\d{2}:\d{2}` anchor); `Compare`/`Less` are lexical. |
| `protocol/` | types.go, conflict.go | Wire types (`SyncRequest`/`SyncResponse`, `Entity`, `Relationship`, `SyncChange`, `Filters`, `ConflictInfo`). Reserved `vector_clock`/`cursor` carried as `json.RawMessage` (round-trip, `omitempty`). `Resolve` = canonical LWW + 1s-window version tiebreak; `Entity.Deleted()` reads `content.deleted`. |
| `store/` | store.go | Durable local cache: in-memory maps persisted atomically to a single JSON file (tmp + rename). Keeps latest version per id (tombstones retained), watermark, pending-push queue. `ApplyBatch` topologically orders parents-before-children. |
| `syncengine/` | sync.go | `Engine` builds full vs. delta `SyncRequest` (delta `filters.since` = persisted `server_time` watermark, never the client clock), applies server changes then advances watermark, clears pending. `HTTPTransport` POSTs `/api/v1/sync/` with `Authorization: Bearer <token>`. |
| `graph/` | graph.go, uuid.go | `Ops` implements the 12 tool behaviours + `DeleteEntity` (tombstone) over the store: search, details, create/update/delete entity, relationships, devices-in-room, controls, room-connections, BFS `find_path`, similarity, procedures, automations. |
| `mcp/` | server.go, tools.go | Stdio JSON-RPC 2.0 (newline-delimited) server. `tools/list` returns exactly the 12 tool descriptors; `tools/call` dispatches to `graph.Ops` and returns a single text-content JSON payload. Handles `initialize`, `ping`, notifications. |
| `cmd/wombat-mcp/` | main.go | Entry point: env config, opens store, initial sync on startup, `backgroundSync` ticker, then serves MCP over stdin/stdout. |
| `conformance/` | conformance_test.go | Loads and asserts against `fixtures/version-strings.json`, `knowledge-graph.json`, `mcp-tool-golden.json`, `sync-exchanges.json` (the wire contract). |

## Flow

`wombat-mcp` → `store.Open` → initial `engine.Sync` (bearer-auth HTTP →
`ApplyBatch` → `SetWatermark`) → `go backgroundSync` → `mcp.Server.Serve` reads
JSON-RPC, dispatches `tools/call` to `graph.Ops`, which reads/writes the durable
store (local writes enqueued as pending changes pushed on the next sync).
