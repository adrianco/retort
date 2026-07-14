# Flow

```mermaid
sequenceDiagram
    participant Client as MCP Client (stdin)
    participant Main as main.go:Serve
    participant MCP as mcp.go:Dispatch
    participant Tools as tools.go:handler
    participant Query as query.go
    participant Format as format.go

    Client->>Main: {"jsonrpc":"2.0","id":1,"method":"initialize",...}
    Main->>MCP: Dispatch(raw)
    MCP-->>Main: {protocolVersion, capabilities, serverInfo}
    Main-->>Client: JSON response + newline

    Client->>Main: {"method":"tools/call","params":{"name":"standings","arguments":{"season":2019}}}
    Main->>MCP: Dispatch(raw)
    MCP->>Tools: handleStandings(ds, args)
    Tools->>Query: ds.Standings("Brasileirão", 2019)
    Query-->>Tools: []StandingRow
    Tools->>Format: FormatStandings(comp, season, table)
    Format-->>Tools: text
    Tools-->>MCP: text, nil
    MCP-->>Main: {result: {content: [{type: "text", text: ...}]}}
    Main-->>Client: JSON response + newline
```

On startup, `main()` resolves the data directory (CLI arg > env var > default), calls `LoadDataset()` which reads all 6 CSVs into a single in-memory `Dataset`, then enters the stdio `Serve` loop. Each line from stdin is unmarshaled as a JSON-RPC request and routed by `Dispatch` — protocol methods (initialize, ping, tools/list) are handled inline; `tools/call` looks up the named tool in the registry, invokes its handler with the dataset and arguments, and wraps the text result in an MCP content block. The response is marshaled and flushed to stdout. Notifications produce no output. The loop runs until EOF.

No concurrency, no caching, no middleware. All queries are full scans of in-memory slices. The standings query picks the single source with the most matches for a season to avoid double-counting across overlapping Brasileirão datasets.
