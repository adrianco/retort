# Flow

Dominant flow: a delta sync round-trip that advances the exclusive watermark, then serves a tool call from the local cache.

```mermaid
sequenceDiagram
    participant Main as cmd/wombat-mcp
    participant Eng as syncengine.Engine
    participant Srv as FunkyGibbon /api/v1/sync/
    participant St as graph.Store
    participant MCP as mcp.Server
    Main->>Eng: Sync(ctx, nil)
    Eng->>St: GetWatermark()
    St-->>Eng: server_time ("" ⇒ full, else delta)
    Eng->>Srv: POST SyncRequest (Bearer token, filters.since = watermark)
    Srv-->>Eng: SyncResponse (changes, conflicts, server_time)
    Eng->>Eng: orderChanges (parents before children)
    Eng->>St: applyEntityChange → conflict.Resolve on version clash
    Eng->>St: PutRelationship (stage 2)
    Eng->>St: SetWatermark(server_time)  (only on full success)
    Note over MCP,St: later — MCP tool call
    MCP->>St: ActiveEntities / RelationshipsFrom/To
    St-->>MCP: cached entities/edges
    MCP-->>MCP: ReducePayload → {content:[{type:text}]}
```

The client persists the response `server_time` and replays it as a strictly-greater-than `filters.since` (never the local clock). Conflict resolution is last-write-wins on `updated_at` (derived from the version timestamp, since the wire form carries no `updated_at`); within a 1-second window the lexically greater `version` string wins. Deletes are tombstones (`content.deleted=true`), retained for sync but excluded from active queries. The cache is a single atomically-written JSON file, so state survives restarts; the graph store guards concurrent background-sync and tool access with a mutex. Initial sync and MCP serving are best-effort/decoupled: a sync failure logs to stderr and the tool surface still serves from the cache offline.
