# Flow

```mermaid
sequenceDiagram
    Client->>index.ts: start (stdio)
    index.ts->>data.ts: loadDataset()
    data.ts-->>index.ts: Dataset (matches, players, league)
    index.ts->>server.ts: createServer(ds) + connect
    Client->>server.ts: callTool search_matches {team, opponent}
    server.ts->>queries.ts: searchMatches(ds, args)
    queries.ts->>teams.ts: resolveTeam / displayName
    queries.ts-->>server.ts: formatted text answer
    server.ts-->>Client: { content: [{type:text}] }
```

On startup `index.ts` loads all six CSVs via `loadDataset()` (parsing dates in multiple formats, normalising team names, deduplicating overlapping sources, and picking one preferred source per Brasileirão season for league tables), then registers 14 MCP tools. Each tool call is wrapped in try/catch: the query functions return a pre-formatted text block, and errors are surfaced as `isError` MCP results rather than thrown. Team inputs are resolved to canonical keys through `teams.ts` (accent-stripping, alias table, state-suffix removal, substring fallback). No network access at query time — all answers come from the in-memory dataset.
