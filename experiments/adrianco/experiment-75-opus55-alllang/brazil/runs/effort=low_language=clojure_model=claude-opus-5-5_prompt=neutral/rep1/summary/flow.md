# Flow

```mermaid
sequenceDiagram
    Client->>server.clj: tools/call {name: "head_to_head", arguments}
    server.clj->>server.clj: handle → call-tool
    server.clj->>data.clj: (db) [delay: load-all, memoized]
    data.clj->>data.clj: read-csv × 6, normalize keys/dates
    data.clj-->>server.clj: {:matches :players :sources}
    server.clj->>query.clj: head-to-head db team-a team-b
    query.clj->>query.clj: resolve-team, find-matches, dedupe, team-record
    query.clj-->>server.clj: {:a-wins :b-wins :draws :matches}
    server.clj->>query.clj: format-h2h
    query.clj-->>server.clj: text
    server.clj-->>Client: {content: [{type: "text", text}]}
```

A `tools/call` request is parsed line-by-line from stdin, routed through `handle` → `call-tool`, which looks the tool up in `tools-by-name` and invokes its handler with the shared, memoized db. The db is a `defonce`+`delay` loaded once (and warmed in a `future` at startup) by reading all six CSVs, canonicalizing team names via `team-key` (accent-stripping, state-suffix disambiguation, alias table) and normalizing dates to ISO. Query functions filter/aggregate the in-memory vectors; `dedupe-matches` collapses the same fixture appearing across files within a 3-day window. Results are formatted to human-readable text and wrapped in the MCP `content` envelope. Errors are caught: protocol/argument errors return JSON-RPC error codes, tool-internal errors return `isError: true` text rather than crashing the loop.
