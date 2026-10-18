# Flow

```mermaid
sequenceDiagram
    Client->>main.rs: spawn, DATA_DIR arg
    main.rs->>data.rs: Dataset::load(dir)
    data.rs-->>main.rs: Dataset (matches, players, sources)
    Client->>main.rs: {"method":"tools/call","name":"search_matches",...}
    main.rs->>mcp.rs: handle_line(ds, line)
    mcp.rs->>tools.rs: call(ds, "search_matches", args)
    tools.rs->>query.rs: find_matches(ds, &filter)
    query.rs->>normalize.rs: team_key(name)
    normalize.rs-->>query.rs: canonical key
    query.rs-->>tools.rs: Vec<&Match> (recent first)
    tools.rs-->>mcp.rs: formatted text
    mcp.rs-->>main.rs: {"result":{"content":[{text}],"isError":false}}
    main.rs-->>Client: response line
```

At startup `main.rs` loads all six CSVs once into an in-memory `Dataset`; match sources
are deduped (same competition + unordered team pair within one day). Each stdin line is a
JSON-RPC message: `mcp.rs:handle_line` dispatches by method, routing `tools/call` to
`tools.rs:call`, which parses/validates arguments and delegates to the pure `query.rs`
functions. Team names are normalized through `normalize.rs:team_key` so variant spellings
(e.g. `Palmeiras-SP`, `Sociedade Esportiva Palmeiras`) collapse to one key. Results are
formatted as human-readable text and returned as an MCP tool result. Argument errors
return `isError:true` rather than a protocol error, so the model can self-correct. Logs go
to stderr to keep the stdout protocol stream clean.
