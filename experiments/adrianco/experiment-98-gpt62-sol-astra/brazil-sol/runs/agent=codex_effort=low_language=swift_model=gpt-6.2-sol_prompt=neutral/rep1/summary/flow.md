# Flow

```mermaid
sequenceDiagram
    Client->>main.swift: {"method":"tools/call","params":{"name":"search_matches",...}}
    main.swift->>MCP.swift: server.response(to: line)
    MCP.swift->>MCP.swift: parse JSON-RPC, validate id/params
    MCP.swift->>MCP.swift: Tool.validate(arguments)
    MCP.swift->>Queries.swift: graph.query("search_matches", args)
    Queries.swift->>Queries.swift: MatchFilter(args).apply(to: graph)
    Queries.swift-->>MCP.swift: {total, offset, matches[...], nextOffset?}
    MCP.swift-->>main.swift: {jsonrpc, id, result:{content, structuredContent}}
    main.swift-->>Client: response line
```

On startup `SoccerGraph(directory:)` reads all six CSVs once, canonicalizes team names, merges duplicate fixtures across the five match sources (with a handful of dataset-specific corrections), and indexes matches by team and players by club. Each `tools/call` then validates arguments against a per-tool JSON schema, dispatches to `query(_:args:)`, and returns both a `structuredContent` object and an equivalent JSON text block. Standings, records and analytics are all computed from the merged match set at request time — nothing is hardcoded. Note: argument-level failures are returned as `isError: true` tool results (not JSON-RPC errors), which is MCP-idiomatic; protocol-level failures use JSON-RPC error codes.
