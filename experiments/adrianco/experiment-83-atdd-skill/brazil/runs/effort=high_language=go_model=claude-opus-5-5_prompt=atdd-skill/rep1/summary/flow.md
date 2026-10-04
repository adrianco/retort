# Flow

```mermaid
sequenceDiagram
    Host->>main.go: start subprocess (-data data/kaggle)
    main.go->>app.Run: args, stdin, stdout, stderr
    app.Run->>soccer.Load: read 6 CSVs
    soccer.Load-->>app.Run: *Store (matches, players, teams)
    app.Run->>mcpserver.Serve: register 20 tools, read stdin
    Host->>mcpserver: {"method":"tools/call","name":"search_matches",...}
    mcpserver->>tools.searchMatches: Args
    tools.searchMatches->>soccer.Store: SearchMatches(query, limit)
    soccer.Store-->>tools.searchMatches: result (Text + Structured)
    tools.searchMatches-->>mcpserver: Result
    mcpserver-->>Host: {"result":{"content":[{text}],"structuredContent":{...}}}
```

An MCP host launches the binary as a subprocess. `app.Run` loads all six Kaggle
CSVs once into an in-memory `Store` (deduping matches recorded by multiple
sources within a 3-day window, inferring Copa do Brasil knockout stages, and
normalizing team names), then serves JSON-RPC line by line over stdin/stdout.
Each `tools/call` is dispatched by name to a handler in `tools.go`, which
coerces the loosely-typed arguments, resolves team/competition names, queries
the `Store`, and returns both a human-readable `Text` rendering and a
`structuredContent` object. Tool-handler errors are returned as MCP error
results (`isError: true`) rather than protocol errors, and a `recover` guards
against handler panics. Notable: no network calls, no persistence, no
pagination state (each call is stateless); all computation is over the
in-memory slices built at startup.
