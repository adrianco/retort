# Flow

```mermaid
sequenceDiagram
    Client->>server.ts: {"method":"tools/call","params":{"name":"search_matches","arguments":{team:"Flamengo"}}}
    server.ts->>service.ts: findMatches(args)
    service.ts->>data.ts: this.data.matches (loaded at construction)
    data.ts-->>service.ts: Match[]
    service.ts->>service.ts: filter by team/competition/season/date, sort desc, slice(limit)
    service.ts-->>server.ts: {count, matches[], truncated}
    server.ts-->>Client: {"jsonrpc":"2.0","id":..,"result":{content:[{type:"text",text:json}],structuredContent:..}}
```

On startup `SoccerData` eagerly reads and parses all six CSVs into `matches`/`players` arrays (synchronous `readFileSync`). Each `tools/call` runs an in-memory linear scan: `findMatches` is the shared primitive that `teamStats`, `headToHead`, and `aggregate` all build on. Notable deviations from common patterns: no official MCP SDK (JSON-RPC is hand-written on a readline loop); tool `inputSchema`s are untyped (`additionalProperties:true`); no input validation beyond required-arg checks; the five match sources are concatenated without de-duplication, so the same real match appears under multiple `source`/`competition` labels (e.g. 2019 Brasileirão is present in both the `brasileirao` and `historical` sources and again as `Serie A` in the extended set).
